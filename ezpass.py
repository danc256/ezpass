#!/usr/bin/env python3

import sys
import os
import pathlib
import shutil
import subprocess
import hashlib
import configparser
from configparser import NoOptionError, NoSectionError
from pathlib import Path

VALIDATION_DIRECTORY_NAME = 'validation'

"""
Contains configuration data. Exposes methods that make it easy for the caller to validate values without baking 
validation knowledge inside configuration class. 
"""


class ConfigData:
    DEFAULT_CONFIG_PATH = '.precheck.ini'
    CONFIG_ENVIRONMENT_OVERRIDE = 'PRECHECK_CONFIG_PATH'
    BASE_CONFIG = 'base_config'
    FILE_RESOURCES = 'file_resources'

    def __init__(self, config_path_override=None):
        # Figure out where we're reading the config file from
        # TODO Add CLI option to specify path explicitly
        self.config_file_path = os.path.abspath(self._get_config_file_path(config_path_override))

        if os.path.isfile(self.config_file_path):
            self.config_data = configparser.ConfigParser()
            self.config_data.read(self.config_file_path)
        else:
            raise FileNotFoundError('Unable to load configuration file at location: %s' % self.config_file_path)

    @classmethod
    def _get_config_file_path(cls, config_path=None):
        # Take location of config file from an environment variable, otherwise use the default location
        if config_path:
            # If a path was specified explicitly just use that
            return config_path
        else:
            # If an environment variable was specified use that, otherwise read a file from the user's home directory
            environment_override = os.environ.get(cls.CONFIG_ENVIRONMENT_OVERRIDE, None)
            if environment_override:
                return environment_override
            else:
                return os.path.join(str(Path.home()), cls.DEFAULT_CONFIG_PATH)

    # Performs no validation on the value other than throwing a exception if it isn't present
    def get(self, section, key):
        try:
            return self.config_data.get(section, key)
        except (NoSectionError, NoOptionError):
            self._raise_lookup_error(section, key, "not found")

    def get_file_path(self, section, key, base_path=None):
        # Retrieve the desired file path
        file_path = self.get(section, key)

        # If a base path was specified and the desired file is only a file name, prepend the base path
        if base_path:
            (parent_path, file) = os.path.split(file_path)
            if not parent_path:
                file_path = os.path.join(base_path, file_path)

        if os.path.isfile(file_path):
            return file_path
        else:
            self._raise_lookup_error(section, key, "the value [%s] is not a file" % file_path)

    def _raise_lookup_error(self, section, key, message):
        raise ValueError(
            "In configuration file [%s], section [%s], key [%s] %s" % (self.config_file_path, section, key, message))


"""
Iterate over all disk images in the immediate folder (no recursion) and run them through Passport.
"""


class ImageValidate:
    DISK_IMAGE_GLOB = '*.woz'

    def __init__(self, config):
        # Base directory where all file resources are loaded (if not fully-qualified)
        base_resource_path = config.get(ConfigData.BASE_CONFIG, 'base_resource_path')

        self.blank_disk_image_path = config.get_file_path(ConfigData.FILE_RESOURCES, 'blank_disk_image_path',
                                                          base_resource_path)

        emulator_type = config.get(ConfigData.BASE_CONFIG, 'emulator')
        self.emulator_automation_runner = config.get_file_path(ConfigData.FILE_RESOURCES, emulator_type,
                                                               base_resource_path)

        self.passport_path = config.get_file_path(ConfigData.FILE_RESOURCES, 'passport_disk_image_path',
                                                  base_resource_path)

    def validate_single_directory(self, raw_directory):
        # Insure that whether we get a relative or absolute path, that we always use the absolute path
        # https://stackoverflow.com/questions/3320406/how-to-check-if-a-path-is-absolute-path-or-relative-path-in-cross-platform-way-w
        base_directory = os.path.abspath(raw_directory)

        if os.path.isdir(base_directory):
            src_disk_image_file_list = self._get_disk_image_files(base_directory)
            self._validate_directory_contents(base_directory, src_disk_image_file_list)
        else:
            raise NotADirectoryError('[%s] is not a directory' % base_directory)

    # TODO Break out emulator interaction (strategy pattern) and report tabulation into separate classes
    def _validate_directory_contents(self, base_directory, src_disk_image_file_list):
        # Create the base validation directory under which a directory will be created for each disk image
        validation_directory = os.path.join(base_directory, VALIDATION_DIRECTORY_NAME)
        if not os.path.isdir(validation_directory):
            os.mkdir(validation_directory)

        # Store the path to validation assets for post-processing and analysis
        target_disk_path_list = list()
        screen_shot_file_path_list = list()
        processing_anomaly_dict = dict()

        for src_disk_image_file_path in src_disk_image_file_list:
            # Use the source image file name as the base name in the validation directory
            src_disk_image_file_name = os.path.split(src_disk_image_file_path)[1]
            src_disk_image_file_name_no_ext = os.path.splitext(src_disk_image_file_name)[0]

            # This is the base filename of all assets created as part of validation
            target_base_file_path = os.path.join(validation_directory, src_disk_image_file_name_no_ext)

            # Copy blank disk to validation directory
            target_disk_image_file_path = target_base_file_path + '.dsk'
            self._copyfile(self.blank_disk_image_path, target_disk_image_file_path, overwrite=False)

            target_disk_path_list.append(target_disk_image_file_path)

            # Run Passport on disk images and create screen shot of results
            screen_shot_file_path = target_base_file_path + '.png'

            print('Processing image file: ' + src_disk_image_file_name_no_ext)
            passport_result_code = self._run_passport(src_disk_image_file_path, target_disk_image_file_path,
                                                      screen_shot_file_path)

            screen_shot_file_path_list.append(screen_shot_file_path)

            if passport_result_code != "OK":
                if passport_result_code not in processing_anomaly_dict.keys():
                    processing_anomaly_dict[passport_result_code] = list()

                processing_anomaly_dict[passport_result_code].append(src_disk_image_file_name)

        processing_anomaly_report = self._generate_process_anomaly_report(processing_anomaly_dict)
        print(processing_anomaly_report)

        process_anomaly_report_file = os.path.join(validation_directory, 'process_anomaly_report.txt')
        with open(process_anomaly_report_file, 'w') as text_file:
            text_file.write(processing_anomaly_report)

        # Open all the screen shots in Preview for easy review
        subprocess.Popen(['/usr/bin/open', *screen_shot_file_path_list])

        # Generate a report for duplicate disk images
        duplicate_report = self._check_for_duplicate_images(target_disk_path_list)
        print(duplicate_report)

        duplicate_report_file = os.path.join(validation_directory, 'duplicate_report.txt')
        with open(duplicate_report_file, 'w') as text_file:
            text_file.write(duplicate_report)

    @staticmethod
    def _generate_process_anomaly_report(process_anomaly):
        report = 'Processing anomaly report\n\n'

        for key in process_anomaly.keys():
            anomalies = process_anomaly[key]
            anomalies.sort()

            report += key + '\n'
            for entry in anomalies:
                report += '  ' + entry + '\n'

            report += '\n'

        return report

    def _check_for_duplicate_images(self, disk_path_list):
        disk_image_hash = dict()

        # Create a dictionary of hash codes for all disk images
        for disk_path in disk_path_list:
            hashcode = self._generate_hash_for_file(disk_path)

            # If this is the first file with this hashcode, create an empty list for this hashcode
            if hashcode not in disk_image_hash.keys():
                disk_image_hash[hashcode] = list()

            # Whether an empty or existing list, append the file name to the list
            disk_image_hash[hashcode].append(os.path.split(disk_path)[1])

        # Iterate over the dictionary and write out any list of values with more than a single entry
        duplicate_count = 0

        sorted_duplicate_list = list()
        for duplicate_list in disk_image_hash.values():
            if len(duplicate_list) > 1:
                duplicate_count += 1

                # Not an ideal programming practice since it modifies the source list but whatever
                duplicate_list.sort(reverse=True)

                sorted_duplicate_list.append(duplicate_list)

        # Generate human-readable duplicate image report
        if duplicate_count == 0:
            report = 'No duplicate images\n\n'
        else:
            report = 'Duplicate image report\n\n'
            # Dump the sorted list of duplicates, if any
            sorted_duplicate_list.sort()

            for duplicate_entry in sorted_duplicate_list:
                for entry in duplicate_entry:
                    report += entry + '\n'

                report += '\n'

        return report

    @staticmethod
    def _generate_hash_for_file(filepath):
        hashcode = hashlib.sha256()

        with open(filepath, 'rb') as file:
            while True:
                data = file.read(65536)
                if not data:
                    break
                hashcode.update(data)

        return hashcode.hexdigest()

    def _run_passport(self, source_disk_path, target_disk_path, screen_shot_path):
        # Kick off an AppleScript that automates Virtual ][ to run Passport on the specified disk images
        process = subprocess.Popen(
            ['/usr/bin/osascript', self.emulator_automation_runner, str(source_disk_path),
             str(target_disk_path),
             str(screen_shot_path),
             str(self.passport_path)
             ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        out, err = process.communicate()

        if process.returncode:
            # This indicates a code bug and means there was a problem invoking AppleScript
            err_message = 'Passport invocation error: ' + str(err.decode('utf-8')).strip()
            raise Exception(err_message)
        else:
            # This is a result code from AppleScript and indicates Passport's processing result
            # OK - No read errors at least
            # FRE - Fatal Read Error (re-image the disk)
            return str(out.decode('utf-8')).strip()

    def _get_disk_image_files(self, directory):
        result = list()

        for file in pathlib.Path(directory).glob(self.DISK_IMAGE_GLOB):
            result.append(file)

        return result

    @staticmethod
    def _copyfile(source_file, target_file, overwrite=False):
        # Unconditionally copy the file
        if overwrite:
            shutil.copyfile(source_file, target_file)
        else:
            # DO NOT copy the file if it already exists
            if not os.path.isfile(target_file):
                shutil.copyfile(source_file, target_file)


def main():
    config = ConfigData()

    if len(sys.argv) == 2:
        as_validate = ImageValidate(config)
        as_validate.validate_single_directory(sys.argv[1])
    else:
        print('You must specify a directory to process')


if __name__ == '__main__':
    main()
