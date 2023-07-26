#!/usr/bin/env python

import utils as ut
import numpy as np
import argparse
import os
import glob
import datetime
from astropy.io import fits
import version as v
import shutil

"""Creates a fringe_model to use in order to suppress fringing on IRiS images.
To create the model, we use the method of Snodgrass & Carry 2013, Messenger 152, 14"""

def create_model(fringe_maps, model_name, folder, N_samples):
    """create the fringe model and save it with the model_name"""

    # creates the model by taking the median of all fringe_maps
    median = np.median(fringe_maps, axis = 0)

    # creating the header with the history of the processing
    hdu = fits.PrimaryHDU()
    header = hdu.header
    header['HISTORY'] = "model done with model.py (version {})".format(v.version_model())
    header['HISTORY'] = 'using the image folder {}'.format(folder)
    header['HISTORY'] = 'with {} image samples'.format(N_samples)
    
    # creates a .fits file to save the model
    ut.create_fits(model_name, median, header)

# functions to correctly read the setup file

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

def read_int(num):
    """convert a string into an int"""
    return int(num)

def do_nothing(x):
    """just a convenient function for after"""
    return x

def read_setup(file, verbose):
    """reads the setup file and returns the information in it"""

    # taking the date for the default model name
    date = datetime.datetime.today()
    year = date.year
    month = date.month
    day = date.day
    time = datetime.datetime.utcnow()
    hour = time.hour
    minute = time.minute
    sec = time.second

    # setting the default parameters
    image_folder = None
    N_samples = None
    model_name = "iris_model_{}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}.fits".format(year, month, day, hour, minute, sec)

    # list of the default parameters
    param_list = [image_folder, N_samples, model_name]

    # displays the default values if verbose
    if verbose:
        print("The default values for each parameter are :")
        print("- image folder : {}".format(image_folder))
        print("- number of samples : {}".format(N_samples))
        print("- model name : {}".format(model_name))
        print("\na message will be displayed each time a value is modified\n")

    # list of all the parameters accepted by the code
    input_list = ['image folder', 'number of samples', 'model name']

    # dictionnary with a function associated to each parameter if necessary to read them correctly
    input_dic = {'image folder' : do_nothing,
                 'number of samples': read_int,
                 'model name' : do_nothing,
                 }

    # checking if there is a file
    if file is not None:
        text = open(file, 'r')
    else:
        print("NO FILE WAS GIVEN.")
        print("a folder name is needed to run the code.")
        print("Please give a setup file with atleast the information about the folder name in which the code will take the images")
        exit()
    
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
            
            # displays the changes if verbose
            if verbose:
                print("the parameter {} was set to {}".format(input, input_value)) 
        except ValueError: # in case the parameter is not in the list (e. g. an empty line)
            pass
    
    if param_list[0] is None: #checks if a folder name was given
        print("NO IMAGE FOLDER GIVEN")
        print("a image folder is needed to run the code.")
        print("Please give a setup file with atleast this piece of information")
        exit()
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
    folder_name, N_samples, model_name = read_setup(f_name, verbose)

    # creating a temporary file in which the _pierside images will be gathered for the model

    path = "tmp_pierside"
    if not os.path.exists(path):
        os.mkdir(path)

    images = glob.glob(folder_name + '\\*.fits')
    for image in images:
        ut.pierside(image, path)

    # first, we gather the fringe maps
    fringe_maps, N_samples = ut.gather_normalized_images(path, N_samples)

    # then we delete the temporary file
    shutil.rmtree(path)

    # finally, we create the model
    create_model(fringe_maps, model_name, folder_name, N_samples)
