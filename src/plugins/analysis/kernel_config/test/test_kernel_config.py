import glob
import sys
from pathlib import Path

from objects.file import FileObject
from test.unit.analysis.analysis_plugin_test_class import AnalysisPluginTest

from ..code.kernel_config import AnalysisPlugin

try:
    from ..internal.decomp import GZDecompressor
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent / 'internal'))
    from decomp import GZDecompressor


TEST_DATA_DIR = Path(__file__).parent / 'data'


class ExtractIKConfigTest(AnalysisPluginTest):
    PLUGIN_NAME = 'kernel_config'

    def setUp(self):
        super().setUp()
        config = self.init_basic_config()
        self.analysis_plugin = AnalysisPlugin(self, config=config)

    def test_probably_kernel_config_true(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        assert self.analysis_plugin.probably_kernel_config(test_file.binary)

    def test_probably_kernel_config_false(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG_MAGIC_CORRUPT'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        assert not self.analysis_plugin.probably_kernel_config(test_file.binary)

    def test_probably_kernel_config_utf_error(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'random_invalid/a.image'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        assert not self.analysis_plugin.probably_kernel_config(test_file.binary)

    def test_process_configs_ko_success(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'synthetic/configs.ko'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        self.analysis_plugin.process_object(test_file)

        assert test_file.processed_analysis[self.PLUGIN_NAME]['is_kernel_config']
        assert len(test_file.processed_analysis[self.PLUGIN_NAME]['kernel_config']) > 0

    def test_process_configs_ko_failure(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'synthetic/ko_failure/configs.ko'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        self.analysis_plugin.process_object(test_file)

        assert 'is_kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]
        assert 'kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]

    def test_process_valid_plain_text(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        self.analysis_plugin.process_object(test_file)

        assert test_file.processed_analysis[self.PLUGIN_NAME]['is_kernel_config']
        assert test_file.processed_analysis[self.PLUGIN_NAME]['kernel_config'] == test_file.binary.decode()

    def test_process_invalid_plain_text(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'random_invalid/c.image'))
        test_file.processed_analysis['file_type'] = dict(mime='text/plain')

        self.analysis_plugin.process_object(test_file)

        assert 'is_kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]
        assert 'kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]

    def test_extract_ko_success(self):
        test_file = FileObject(file_path=str(TEST_DATA_DIR / 'synthetic/configs.ko'))
        test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
        test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

        result = AnalysisPlugin.try_object_extract_ikconfig(test_file.binary)

        assert len(result) > 0
        assert self.analysis_plugin.probably_kernel_config(result)

    def test_process_objects_kernel_image(self):
        for valid_image in glob.glob(str(TEST_DATA_DIR / 'synthetic/*.image')):
            test_file = FileObject(file_path=str(valid_image))
            test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
            test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

            self.analysis_plugin.process_object(test_file)

            assert test_file.processed_analysis[self.PLUGIN_NAME]['is_kernel_config']
            assert len(test_file.processed_analysis[self.PLUGIN_NAME]['kernel_config']) > 0

        for bad_image in glob.glob(str(TEST_DATA_DIR / 'random_invalid/*.image')):
            test_file = FileObject(file_path=str(bad_image))
            test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
            test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

            self.analysis_plugin.process_object(test_file)

            assert 'is_kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]
            assert 'kernel_config' not in test_file.processed_analysis[self.PLUGIN_NAME]


def test_plaintext_mime_true():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
    test_file.processed_analysis['file_type'] = dict(mime='text/plain')

    assert AnalysisPlugin.object_mime_is_plaintext(test_file)


def test_plaintext_mime_false():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
    test_file.processed_analysis['file_type'] = dict(mime='application/json')

    assert not AnalysisPlugin.object_mime_is_plaintext(test_file)


def test_try_extract_decompress_fail():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'synthetic/configs.ko.corrupted'))
    test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
    test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

    assert AnalysisPlugin.try_object_extract_ikconfig(test_file.binary) == b''


def test_is_kernel_image_true():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
    test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
    test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

    assert AnalysisPlugin.object_is_kernel_image(test_file)


def test_is_kernel_image_false():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
    test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
    test_file.processed_analysis['software_components'] = dict(summary=['FreeBSD Kernel'])

    assert not AnalysisPlugin.object_is_kernel_image(test_file)


def test_try_extract_fail():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG'))
    test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
    test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])

    assert AnalysisPlugin.try_object_extract_ikconfig(test_file.binary) == b''


def test_try_extract_random_fail():
    for fp in glob.glob(str(TEST_DATA_DIR / 'random_invalid/*.image')):
        test_file = FileObject(file_path=fp)
        test_file.processed_analysis['file_type'] = dict(mime='application/octet-stream')
        test_file.processed_analysis['software_components'] = dict(summary=['Linux Kernel'])
        assert AnalysisPlugin.try_object_extract_ikconfig(test_file.binary) == b''


def test_gz_break_on_true():
    test_file = FileObject(file_path=str(TEST_DATA_DIR / 'configs/CONFIG.gz'))
    decompressor = GZDecompressor()
    assert decompressor.decompress(test_file.binary) != b''


def test_checksec_existing_config():
    test_file = TEST_DATA_DIR / 'configs/CONFIG'
    kernel_config = test_file.read_text()
    result = AnalysisPlugin.check_kernel_config(kernel_config)
    assert result != {}
    assert 'kernel' in result
    assert 'selinux' in result
    assert 'grsecurity' in result
    assert 'randomize_va_space' not in result['kernel']
    assert result['kernel']['kernel_heap_randomization'] == 'yes'


def test_checksec_no_valid_json(monkeypatch):
    invalid_json = 'invalid_json'
    monkeypatch.setattr('plugins.analysis.kernel_config.code.kernel_config.execute_shell_command', lambda _: invalid_json)
    result = AnalysisPlugin.check_kernel_config('no_real_config')
    assert result == {}