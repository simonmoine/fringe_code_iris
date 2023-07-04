#!/usr/bin/env python

import utils as ut
import wget
import urllib.request
from urllib.error import HTTPError, ContentTooShortError
import os
from zipfile import ZipFile, BadZipFile
import glob
import shutil
import time
from astropy.io import fits
import argparse
import datetime

"""Automatically gathers images from the IRiS telescope at http://cesam.lam.fr/iris/."""

def gather_url(date1, date2):
    """Gathers all the zip URLs to download the observations
    between date1 and date2 (date1 <= date2).
    
    The dates (type : int) should be written as YYYYMMDD."""

    url = "http://cesam.lam.fr/iris/"
    reponse = urllib.request.urlopen(url)

    content = reponse.read().decode('UTF-8') # contains the HTML code of the page (str)

    content = content.split('\n')
    
    urls = [] # list which will contain the urls demanded

    # searching the urls wanted in the page 
    for line in content:
        line = line.strip() # clear all the tabs

        # searches the urls to save and verify the date
        expr1 = "http://iris.lam.fr/observations/" in line
        expr2 = ".zip" in line 
        expr3 = "-calib" not in line # we don't want calibration zips
        if expr1 and expr2 and expr3:

            # gets the date
            line = line.split("http://iris.lam.fr/observations/")[-1]
            line = line.split(".zip")[0]
            date = int(line) 

            # compares with the interval given
            if date1 <= date and date2 >= date:
                urls.append("http://iris.lam.fr/observations/" + line + ".zip") # takes the zip url

    return urls
    
def gather_images(date1, date2, band, folder_name, shape, fco):
    """Gather all the images of IRiS in a given band,
    between date1 and date2 (date1 <= date2).
    Plus, we only keep the images with a given shape.

    Band must be one of those strings : 'u', 'g', 'r', 'i', 'z', 'OIII', 'CH4', 'H-alpha'.

    The images are saved in a folder, given by folder_name.
    finally, the argument fco is used to indicate if we want only the first capture
    of a set of images aiming at the same target the same day (fco = True), or not (fco = False)
    """

    t0 = int(time.time()) # to print the time of extraction at the end

    # checks that the band chosen exists
    bands = ['u', 'g', 'r', 'i', 'z', 'OIII', 'CH4', 'Halpha']
    if band not in bands :
        print("THE BAND CHOSEN DOES NOT EXISTS")
        print("EXITING")
        exit()

    # creating the folder if it does not exists
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    # creation of a temporary file where the zips are extracted
    tmp_path = "tmp"
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)

    urls = gather_url(date1, date2) # gets the zip urls

    print("sorting image of {}-band : {} zips".format(band, len(urls)))

    seen_list = [] # memorize the targets seen, for fco

    # processing all zip urls
    for url in urls:

        zipname = url.strip("http://iris.lam.fr/observations/").strip(".zip") + ".zip"
        print("\nextracting file : {}".format(zipname))

        # downloading the zipfile 
        try:
            wget.download(url, zipname)
        except (HTTPError, ContentTooShortError):
            print("\nthe first downloading failed, it will begin again in 5s")
            try:
                time.sleep(5)
                wget.download(url, zipname)
            except (HTTPError, ContentTooShortError):
                print("\nthe downloading failed again, the images within the zipfile won't appear in the final folder")

        # extracting the zip and deleting it
        try:
            with ZipFile(zipname, 'r') as zip:
                zip.extractall("tmp")
        except BadZipFile: # in case theres is a problem while downloading the file
            print("\nthe file {} was not correctly downloaded. Its images won't appear in the final folder".format(zipname))
        
        os.remove(zipname)

        images = glob.glob(tmp_path + "\\*") # gets all the images in the temporary file
        
        # getting only the images wanted
        for image in images:
            
            # checking all conditions on the images

            if ".fits" not in image: # verify the extension
                continue
            if ("_" + band) not in image: # the condition to select the correct band 
                continue
            if "RAW" in image: # we don't want raw images
                continue

            with fits.open(image) as f:
                header = f[0].header

            # checking the shape of the image
            s1 = header['NAXIS1']
            s2 = header['NAXIS2']

            if (s1, s2) != shape: # condition on the size of the image
                continue
            
            if 'HISTORY' in header: # condition on the calibration of the image, which can be found in the header's history
                history = header['HISTORY']
                history = str(history)
                bias = ('Bias' in history)
                dark = ('Dark' in history)
                flat = ('Flat' in history)
                if not (dark and bias and flat):
                    continue
            else:
                continue

            if fco and 'OBJECT' in header: # checking if it is the first time the target of the image is seen in the zip
                target = header['OBJECT'].strip()
                if target in seen_list:
                    continue
                else:
                    seen_list.append(target)

            # if all the previous checks are passed, moving the image

            image_name = image.split(tmp_path + "\\")[-1]
            dir = folder_name + "\\" + image_name
            if not os.path.exists(dir):
                shutil.move(image, dir)

        # removes what's inside the temporary folder                    
        to_remove = glob.glob(tmp_path + "\\*.fits")
        for im in to_remove:
            os.remove(im)
        # removes the temporary files that could have been created during the extraction of the zip
        remove_tmp = glob.glob("*.tmp")
        for tmp in remove_tmp:
            os.remove(tmp)
    
    os.rmdir(tmp_path)

    t = int(time.time() - t0)

    print("\nextraction done in {} min {} s".format(t // 60, t % 60))


# functions to properly read the setup file if one is given.    

def read_parameter(text):
    """reads a string with the format {parameter} \t ...
    and returns the string parameter"""
    parameter = text.split('\t')[0]
    return parameter.strip()

def take_input(txt):
    """reads a text line with the format {text} \t {text} \t ...
    and returns the last bloc of text, stripped, which is assumed to be
    the input for a given parameter"""
    input = txt.split('\t')[-1]
    return input.strip()

def read_date(date):
    """reads a string date with the format "YYYY/MM/DD"
    and returns an int associated with the format YYYYMMDD"""
    date = date.split('/')
    date = int(''.join(date))
    return date

def read_shape(shape):
    """reads a string shape with the format s1 x s2
    and returns the tuple (s1, s2)"""
    shape = shape.split('x')
    s1 = int(shape[0].strip())
    s2 = int(shape[1].strip())
    shape = (s1, s2)
    return shape

def read_bool(bool):
    """reads a string bollean and returns the boolean associated"""
    if bool == "True" or bool == "true":
        return True
    else:
        return False
    
def do_nothing(x):
    """just a convenient function for after"""
    return x

def read_setup(file, verbose):
    """reads the setup file and returns the information in it"""
    
    # setting the default parameters
    band = 'i' 
    date = datetime.date.today()
    year = date.year
    month = date.month
    day = date.day
    beg_date = int("{:04d}{:02d}{:02d}".format(year-1, month, day))
    end_date = int("{:04d}{:02d}{:02d}".format(year, month, day))
    folder_name = "iris_{}_band_{}_{}".format(band, beg_date, end_date)
    shape = (2048, 2048)
    fco = True

    # list of the default parameters
    param_list = [band, beg_date, end_date, folder_name, shape, fco]

    # displays the default values if verbose
    if verbose:
        print("The default values for each parameter are :")
        print("- band : {}".format(band))
        print("- beginning date : {}".format(beg_date))
        print("- ending date : {}".format(end_date))
        print("- folder_name : iris_{band}_band_{beginning_date}_{ending_date}")
        print("- image shape : {}".format(shape))
        print("- first capture only : {}".format(fco))
        print("\na message will be displayed each time a value is modified\n")

    # list of all the parameters accepted by the code
    input_list = ['band', 'beg date', 'end date', 'folder name', 'image shape', 'first capture only']

    # dictionnary with a function associated to each parameter if necessary to read them correctly
    input_dic = {'band' : do_nothing,
                 'beg date': read_date,
                 'end date' : read_date,
                 'folder name' : do_nothing,
                 'image shape' : read_shape,
                 'first capture only' : read_bool}

    # control of the explicit modification of the folder name
    folder_check = False

    # checking if there is a file
    if file is not None:
        text = open(file, 'r')
    else:
        print("no file was given, the parameters will stay at their default value\n")
        return param_list
    
    # reads all the lines in the file and modify the parameters
    for line in text:
        to_read = line.split("#")[0].strip() # we don't read the comments
        param = read_parameter(to_read) # taking the parameter which will be modified
        try:
            input_value = take_input(to_read) # taking the input value, to convert after

            # converting the input value for the code, using a dictionnary of functions
            param_idx = input_list.index(param) 
            input = input_list[param_idx]
            input_value = input_dic[input](input_value)
            param_list[param_idx] = input_value

            # actualising the folder_name with the correct date if the folder_name is not given in the file
            if input == "folder name":
                folder_check = True
            elif folder_check == False: # actualising the dolfer name while a folder name is not read by the code
                param_list[3] = "iris_{}_band_{}_{}".format(param_list[0], param_list[1], param_list[2])
            
            # displays the changes if verbose
            if verbose:
                print("the parameter {} was set to {}".format(input, input_value)) 
        except ValueError: # in case the parameter is not in the list (e. g. an empty line)
            pass
    print('\n')
    text.close()

    return tuple(param_list) 

if __name__ == "__main__":
    # parsing the arguments 

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help="setup file needed to execute the code")
    parser.add_argument('-v', '--verbose', help="gives more information", action="store_true")
    args = parser.parse_args()
    f_name = args.file
    verbose = args.verbose

    # reading the setup file
    band, beg_date, end_date, folder_name, shape, fco = read_setup(f_name, verbose)

    # gathering the images
    gather_images(beg_date, end_date, band, folder_name, shape, fco)