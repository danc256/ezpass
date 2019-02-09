# EZPass

A tool to automate running *Passport by 4am* on a single folder of WOZ images. The tool takes a folder as an argument, and creates a new folder named *validate* inside with all output artifacts.

## GettingStarted

* Currently only [Virtual II](http://www.virtualii.com/) is supported
    - Because Virtual II only runs on macOS, you will also need a Mac computer
    - Other emulators may be supported if there is interest and a suitable automation facility
* Download the latest copy of [Passport by 4am](https://github.com/a2-4am/passport/releases)   
* EZPass was written using Python 3.7.2 using [Anaconda](https://www.anaconda.com/distribution/)
    - It was not yet tested with CPython
* You will need at least one folder containing at least 1 [WOZ](https://applesaucefdc.com/woz/) disk image

### Installing

* For now there is no distribution package, so clone the repository to a directory of your choice
* Copy the Passport disk image to the `resources` folder in the project directory structure
* Copy (or symlink) the `precheck.ini` file to the root of your user home directory and name the file `.precheck.ini`
    - Alternatively define an environment variable named `PRECHECK_CONFIG_PATH` with the fully-qualified path to your configuration file location
* Edit your configuration file
    - Set `base_resource_path` to the fully-qualified path of the project `resources` folder
    - Set `passport_disk_image_path` to the name of your Passport disk image
* Add ezpass.py to your path
    - Ex: `ln -s /full/path/to/ezpass.py /usr/local/bin`

## Running

Currently the tool takes a single directory as an argument. The specified directory should contain WOZ disk images at the top level. The tool does not check for sub-directories or other disk image types.

On completion of each Passport invocation a screenshot of the results will be saved alongside the output DSK image. Once all images in a directory are processed these screenshots are opened in `Preview` for easy verification.

A duplication report is generated by comparing SHA256 hashes of the target disk images against each other. There is also an anomaly report that is currently somewhat broken. There are a broader range of messages output by Passport than originally anticipated. Sometimes relevant information scrolls off the screen in some cases. This facility may be cleaned up in the future or removed entirely.

## License

This project is licensed under the MIT License - see [LICENSE.txt](LICENSE.txt) file for details

## Acknowledgements (alphabetically)

* [4am](https://github.com/a2-4am) (Passport)
* [Disk Blitz](https://applesaucefdc.com/) (AppleSauce, WOZ format)
* [Gerard Putter](http://www.virtualii.com/) (Virtual II)