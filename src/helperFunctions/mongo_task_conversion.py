import logging
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from werkzeug.datastructures import FileStorage
from werkzeug.wrappers import Request

from helperFunctions.uid import create_uid
from objects.file import FileObject
from objects.firmware import Firmware

OPTIONAL_FIELDS = ['tags', 'device_part']
DROPDOWN_FIELDS = ['device_class', 'vendor', 'device_name', 'device_part']


def create_analysis_task(request):
    task = _get_meta_from_request(request)
    if request.files['file']:
        task['file_name'], task['binary'] = get_file_name_and_binary_from_request(request)
    task['uid'] = get_uid_of_analysis_task(task)
    if task['release_date'] == '':
        # set default value if date field is empty
        task['release_date'] = '1970-01-01'
    return task


def get_file_name_and_binary_from_request(request: Request):
    try:
        file_name = request.files['file'].filename
    except (AttributeError, KeyError):
        file_name = 'no name'
    binary = get_uploaded_file_binary(request.files['file'])
    return file_name, binary


def create_re_analyze_task(request, uid):
    task = _get_meta_from_request(request)
    task['uid'] = uid
    if not task['release_date']:
        task['release_date'] = '1970-01-01'
    return task


def _get_meta_from_request(request):
    meta = {
        'device_name': request.form['device_name'],
        'device_part': request.form['device_part'],
        'device_class': request.form['device_class'],
        'vendor': request.form['vendor'],
        'version': request.form['version'],
        'release_date': request.form['release_date'],
        'requested_analysis_systems': request.form.getlist('analysis_systems'),
        'tags': request.form['tags']
    }
    _get_meta_from_dropdowns(meta, request)

    if 'file_name' in request.form.keys():
        meta['file_name'] = request.form['file_name']
    return meta


def _get_meta_from_dropdowns(meta, request):
    for item in meta.keys():
        if not meta[item] and item in DROPDOWN_FIELDS:
            dd = request.form['{}_dropdown'.format(item)]
            if dd != 'new entry':
                meta[item] = dd


def _get_tag_list(tag_string):
    if tag_string == '':
        return []
    return tag_string.split(',')


def convert_analysis_task(analysis_task: dict):
    fo = convert_analysis_task_to_fo(analysis_task)
    fw = convert_analysis_task_to_fw(analysis_task, fo.get_uid())
    return fo, fw


def convert_analysis_task_to_fo(analysis_task) -> FileObject:
    fo = FileObject(scheduled_analysis=analysis_task['requested_analysis_systems'], is_root=True)
    if 'binary' in analysis_task.keys():
        fo.set_binary(analysis_task['binary'])
        fo.file_name = analysis_task['file_name']
    else:
        if 'file_name' in analysis_task.keys():
            fo.file_name = analysis_task['file_name']
        fo.overwrite_uid(analysis_task['uid'])
    return fo


def convert_analysis_task_to_fw(analysis_task: dict, uid: str) -> Firmware:
    fw = Firmware(
        uid=uid,
        device_class=analysis_task['device_class'],
        vendor=analysis_task['vendor'],
        device_name=analysis_task['device_name'],
        version=analysis_task['version'],
        release_date=analysis_task['release_date']
    )
    fw.device_part = analysis_task['device_part']
    for tag in _get_tag_list(analysis_task['tags']):
        fw.set_tag(tag)
    return fw


def get_uid_of_analysis_task(analysis_task):
    if analysis_task['binary']:
        uid = create_uid(analysis_task['binary'])
        return uid
    return None


def get_uploaded_file_binary(request_file: FileStorage) -> Optional[bytes]:
    with TemporaryDirectory(prefix='faf_upload_') as tmp_dir:
        tmp_file_path = Path(tmp_dir) / 'upload.bin'
        try:
            request_file.save(str(tmp_file_path))
            binary = tmp_file_path.read_bytes()
            return binary
        except (OSError, AttributeError):
            return None


def check_for_errors(analysis_task):
    error = {}
    for key in analysis_task:
        if analysis_task[key] in [None, '', b''] and key not in OPTIONAL_FIELDS:
            error.update({key: 'Please specify the {}'.format(key.replace('_', ' '))})
    return error


def is_sanitized_entry(entry):
    try:
        if re.search(r'_[0-9a-f]{64}_[0-9]+', entry) is None:
            return False
        return True
    except TypeError:  # DB entry has type other than string (e.g. integer or float)
        return False
    except Exception as exception:
        logging.error('Could not determine entry sanitization state: {} {}'.format(sys.exc_info()[0].__name__, exception))
        return False
