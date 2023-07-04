# !/usr/bin/env python

import utils as ut
from astropy.io import fits
import numpy as np
import argparse
import glob
import version as v
    
"""Code which removes the fringing from the images of IRiS."""

def flip_image(image):
    shape = image.shape
    image = image.flatten()
    image = image[::-1] # rotation
    image = np.reshape(image, shape)
    return image

def delta_flux_ref(pairs, model_name, delta_pixel):
    """calculates the variation of light flux between the two
    ends of each control pairs from "pairs", and put the results in an array delta_flux.
    The value at the end of a pair is done by calculating the mean of the pixel values
    in a square box. The half width of the box is given by bow_width
    
    returns the delta_flux_model and the model matrix normalized"""

    # getting the model
    with fits.open(model_name) as f:
        model = f[0].data

    # getting all the coordinates of the ends of the pairs
    y1, x1, y2, x2 = pairs

    # creating the array delta_flux
    n_pairs = len(x1)
    delta_flux = np.zeros(n_pairs)

    # calculating all the delta flux
    for i in range(n_pairs):
        model_plus = np.mean(model[x1[i] - delta_pixel: x1[i] + 1 + delta_pixel, y1[i] - delta_pixel: y1[i] + 1 + delta_pixel])
        model_minus = np.mean(model[x2[i] - delta_pixel: x2[i] + 1 + delta_pixel, y2[i] - delta_pixel: y2[i] + 1 + delta_pixel])
        d_flux = (model_plus - model_minus)
        delta_flux[i] = d_flux

    return delta_flux, model

def ratio_med(pairs, delta_flux_model, image, delta_pixel):
    """calculates the median ratio between the delta_flux of the model
    and the delta_flux of the image
    The value at the end of a pair (given in the pairs tuple) is done by calculating the mean of the pixel values
    in a square box. The half width of the box is given by bow_width
    
    returns the median ratio and the image matrix normalized"""

    # collecting the pairs    
    y1, x1, y2, x2 = pairs

    # creating the delta_flux array for the image
    n_pairs = delta_flux_model.size
    delta_flux_image = np.zeros(n_pairs)

    # calcultates the delta_flux on the image
    for i in range(n_pairs):
        image_plus = np.mean(image[x1[i] - delta_pixel: x1[i] + 1 + delta_pixel, y1[i] - delta_pixel: y1[i] + 1 + delta_pixel])
        image_minus = np.mean(image[x2[i] - delta_pixel: x2[i] + 1 + delta_pixel, y2[i] - delta_pixel: y2[i] + 1 + delta_pixel])
        d_flux = (image_plus - image_minus)
        delta_flux_image[i] = d_flux

    # calculates the ratios and takes the median
    ratio = (delta_flux_image/delta_flux_model)
    median = np.median(ratio)

    return median

def remove(pairs, model, delta_flux_model, image_name, delta_pixel, model_name, control):
    """removes the fringing on the image with the name
    image_name, given some control pairs (given by "pairs") and the array
    of delta_flux of the model corresponding to these pairs
    The value at the end of a pair is done by calculating the mean of the pixel values
    in a square box. The half width of the box is given by bow_width"""

    # writing the changes in the header's history
    with fits.open(image_name) as f:
        image = f[0].data
        header = f[0].header
        header['HISTORY'] = "fringing removed with remove_fringing.py (version {})".format(v.version_remove())
        header['HISTORY'] = "using the model {}".format(model_name)
        header['HISTORY'] = "using the control pairs {}".format(control)
        header['HISTORY'] = "mean done with a box width of {} pixels".format(2 * delta_pixel + 1)
    pierside = header['PIERSIDE'].strip()
    if pierside == 'WEST':
        image = flip_image(image)

    # subtraction of the model to the initial image
    ratio = ratio_med(pairs, delta_flux_model, image, delta_pixel)
    image = image - ratio * model
    if pierside == 'WEST':
        image = flip_image(image)
    
    # saving the new image
    file_name = image_name.split(".fits")[0] + "_fringecor.fits"
    ut.create_fits(file_name, image, header)

# functions to correctly read the setup file

def read_pairs(control):
    """Reads a .xml or .reg file obtained with the region option in ds9.
    extracts the control pairs of the file and creates 4 lists:
    
    x1, y1 : coordinates of the bright end of the pair
    x2, y2 : coordinates of the dark end of the pair"""

    x1, y1, x2, y2 = [], [], [], []

    with open(control) as f:
        for i in range(3):
            f.readline() # the 3 first lines don't interest us

        for line in f:

            # we manipulate the string to gather the information we want
            line = line.strip()
            line = line.split(' ')[0]
            coords = (line.split('(')[1]).split(')')[0]
            coords = coords.split(',')
            x1.append(int(float(coords[0]))-1)
            y1.append(int(float(coords[1]))-1)
            x2.append(int(float(coords[2]))-1)
            y2.append(int(float(coords[3]))-1)

    return x1, y1, x2, y2

def read_fits(name):
    """put a .fits extension to a given name in argument"""
    return name + ".fits"

def do_nothing(x):
    """just a convenient function for after"""
    return x

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

def read_setup(file, verbose):
    """reads the setup file and returns the information in it"""

    # setting the default parameters
    image_name = None
    folder_name = None
    model_name = None
    control = None
    box_width = 11

    # list of the default parameters
    param_list = [image_name, folder_name, model_name, control, box_width]
    pairs_file = None # to return the pairs file at the end for the history in the clean image header

    # displays the default values if verbose
    if verbose:
        print("The default values for each parameter are :")
        print("- image name : {}".format(image_name))
        print("- folder name : {}".format(folder_name))
        print("- model name : {}".format(model_name))
        print("- control pairs : {}".format(control))
        print("- box width : {}".format(box_width))
        print("\na message will be displayed each time a value is modified\n")

    # list of all the parameters accepted by the code
    input_list = ['image name', 'folder name', 'model name', 'control pairs', 'box width']

    # dictionnary with a function associated to each parameter if necessary to read them correctly
    input_dic = {'image name' : do_nothing,
                 'folder name': do_nothing,
                 'model name' : do_nothing,
                 'control pairs' : read_pairs,
                 'box width' : read_int
                 }

    # checking if there is a file
    if file is not None:
        text = open(file, 'r')
    else:
        print("NO FILE WAS GIVEN.")
        print("an image name (or a folder name), a model name and some control pairs are needed to run the code.")
        print("Please give a setup file with atleast these information")
        exit()
    
    # reads all the lines in the file and modify the parameters
    for line in text:
        to_read = line.split("#")[0].strip() # we don't read the comments
        param = read_parameter(to_read) # taking the parameter which will be modified
        try:
            input_value = take_input(to_read) # taking the input value, to convert after
            
            # saving the pairs file
            if param == "control pairs":
                print("vu")
                pairs_file = input_value

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

    text.close() #closing the file
    
    # errors
    if (param_list[0] is None) and (param_list[1] is None): # checks if a image name or a folder name was given
        print("\nNO FOLDER OR IMAGE NAME GIVEN")
        print("an image name (or a folder name) is needed to run the code.")
        print("Please give a setup file with atleast this piece of information")
        exit()
    if param_list[2] is None: # checks the presence of a model name
        print("\nNO MODEL NAME GIVEN")
        print("a model name is needed to run the code.")
        print("Please give a setup file with atleast this piece of information")
        exit()
    if param_list[3] is None: # checks the presence of control pairs
        print("\nNO CONTROL PAIRS GIVEN")
        print("a control pairs file is needed to run the code.")
        print("Please give a setup file with atleast this piece of information")
        exit()
    
    # in the case where a foler name and an image name are both given in the setup file, the code choose the folder
    # in addition to the information in the folder, the code returns a boolean :
    # True if it returns a folder name, False if it returns an image name
    if (param_list[0] is not None) and (param_list[1] is not None): # returns a folder_name
        if verbose:
            print("\nan image name and a folder name were given, the code will run on the folder\n")
        return tuple(param_list[1:]), pairs_file, True
    elif param_list[0] is None: # same
        return tuple(param_list[1:]), pairs_file, True
    else: # returns an image name
        return tuple([param_list[0]] + param_list[2:]), pairs_file, False

if __name__ == '__main__':
    # parsing the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help="setup file needed to execute the code")
    parser.add_argument('-v', '--verbose', help="gives more information", action="store_true")
    args = parser.parse_args()
    f_name = args.file
    verbose = args.verbose

    # reading the setup file
    (file_name, model_name, pairs, box_width), control, folder_check = read_setup(f_name, verbose)
    
    # calculating the delta_pixel for the slices necessary to mean the values in the following functions
    delta_pixel = box_width // 2
    if verbose:
        print("the box width used is {} pixels".format(2*delta_pixel + 1))

    # obtaining model and delta_flux_model east and west, depending on the images pierside
    delta_flux_model, model = delta_flux_ref(pairs, model_name, delta_pixel)

    # reducing the image or the images
    if folder_check == False:
        remove(pairs, model, delta_flux_model, file_name, delta_pixel, model_name, control)
        if verbose:
            print("\n{} was succesfully reduced".format(file_name))
    else:    
        images = glob.glob(file_name + "\\*.fits")
        for im in images:
            remove(pairs, model, delta_flux_model, im, delta_pixel, model_name, control)
            if verbose:
                print("{} reduced".format(im))