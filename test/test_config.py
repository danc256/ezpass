import pytest
import os
from pathlib import Path

from ezpass import ConfigData

TEST_CONFIG_INI = 'test_config.ini'


@pytest.fixture(scope='session', autouse=True)
def data_dir(pytestconfig):
    return pytestconfig.rootdir.join('resources')


@pytest.fixture()
def config_data(data_dir):
    # Use test config file for all value testing
    return ConfigData(os.path.join(data_dir, TEST_CONFIG_INI));


def test_config_value_present(config_data):
    assert config_data.get(ConfigData.BASE_CONFIG, 'emulator') == 'testemu'


def test_config_value_undefined(config_data):
    with pytest.raises(ValueError):
        assert config_data.get(ConfigData.BASE_CONFIG, 'nosuchvalue') is None


def test_config_section_undefined(config_data):
    with pytest.raises(ValueError):
        assert config_data.get('nosuchvalue', 'emulator') is None


def test_explicit_config_path():
    assert ConfigData._get_config_file_path('dummy') == 'dummy'


# Sloppy. This test has to run before the one that sets the environment variable. Having issues insuring the
# environment variable is clear before running this test.
def test_default_config_path():
    (parent, base) = os.path.split(ConfigData._get_config_file_path())
    assert parent == str(Path.home())


def test_environment_config_path(data_dir):
    test_path = os.path.join(data_dir, 'test_config_environment.ini')
    os.environ[ConfigData.CONFIG_ENVIRONMENT_OVERRIDE] = test_path
    assert ConfigData._get_config_file_path() == test_path


def test_get_file_with_exlicit_data_directory(config_data, data_dir):
    assert config_data.get_file_path(ConfigData.FILE_RESOURCES, 'test_config', data_dir) is not None
