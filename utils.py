# !/usr/bin/env python

import os
import numpy as np
from astropy.io import fits
from random import shuffle
import sys
import glob
import shutil
from astropy.stats import sigma_clipped_stats

"""gathers all the useful function for the code"""

def pierside(image_name, path):
    """check if the pierside of an image is East or West
    if West, we rotate the image of 180°.
    
    image_name : string, the name of the .fits image.
    At the end, it creates a new .fits file in the path indicated."""
    
    # we get the piece of information we want
    with fits.open(image_name) as image:
        data = image[0].data
        shape = data.shape
        header = image[0].header
        pierside = header['PIERSIDE']
        pierside = pierside.strip()

    name = image_name.split('\\')[-1]
    name = path + '\\' + name.split('.fits')[0] + '_pierside.fits'
    if pierside == 'WEST':
        # then we rotate the image
        data = data.flatten()
        data = data[::-1] # rotation
        data = np.reshape(data, shape)
        # then we update the image file and write it in the history
        header['PIERSIDE'] = 'EAST    '
        header['HISTORY'] = "The image was returned to have an 'EAST' pierside"

    create_fits(name, data, header) 


"""the following functions are taken from the fringez code of
https://authors.library.caltech.edu/109403/3/Medford_2021_PASP_133_064503.pdf, 
which are directly useful for our code."""

def create_fits(image_name,
                data,
                header=None):
    """Creates a fits image with an optional header

    Uses the astropy.io.fits pacakge to create a fits image.
    WARNING : THIS WILL OVERWRITE ANY FILE ALREADY NAMED 'image_name'.
    """
    # Creates the Header Data Unit
    hdu = fits.PrimaryHDU(data)

    # Adds the 'header' if None is not selected
    if header is not None:
        hdu.header = header

    # Remove the image if it currently exists
    if os.path.exists(image_name):
        os.remove(image_name)

    # Write the fits image to disk
    hdu.writeto(image_name)

def update_fits(image_name,
                data=None,
                header=None):
    """Safely replaces a fits image with new data and/or header

    Uses the astropy.io.fits pacakge. astropy.io.fits.writeto contains a
    clobber parameter which should allow replacement of one fits file by
    another of the same name with new data(s) and/or header(s). However if the
    rewrite is interupted then the original file is lost as well. This method
    eliminates this risk by guaranteeing that there is always a time where the
    original data is still safely on disk.

    Args:
        image_name : str
            Name of the image.
        data : numpy.ndarray
            2-dimensional array of 'float' or 'int'.
        header : astropy.io.fits.header.Header
            Header of the fits image.

    Returns:
        None

    """

    if data is None and header is None:
        with fits.open(image_name) as f:
            data = f[0].data
            header = f[0].header # nothing is changed

    # Write the fits image to a temporary file
    image_tmp = image_name.replace("fits", "fits.tmp")
    fits.writeto(image_tmp,
                 data,
                 header,
                 overwrite=True)

    # Remove the original image
    if os.path.exists(image_name):
        os.remove(image_name)

    # Rename the temporary image name to the original image name
    shutil.move(image_tmp, image_name)

def gather_normalized_images(file, N_samples=None):
    """gather all the images, centers them, and send them in "file"
    
    N_samples : number of samples for the model.
    if N_samples = None, then N_samples = N_images
    file : file in which the images gathered will be moved"""

    # gets all the images
    fringe_filename_arr = glob.glob(file + '\\*.fits')

    # we convert fringe_file_arr in an array
    fringe_filename_arr = np.array(fringe_filename_arr)
    N_images = len(fringe_filename_arr)

    # shuffling in order to have diversity in a sample
    # in case N_sample != N_images
    shuffle(fringe_filename_arr)
      
    # Determines the image_shape
    with fits.open(fringe_filename_arr[0]) as f:
        image_shape = f[0].data.shape

    # Calculates the size of the samples

    # definition of N_samples in case N_samples == 0

    if N_samples is None:
        N_samples = N_images
    N_images_per_sample = int(N_images / N_samples)
    print('%i image on disk | %i samples -> ~%i images per sample' % (N_images,
                                                                      N_samples,
                                                                      N_images_per_sample))

    fringe_maps = []

    # processing of each sample
    for id_sample in range(N_samples):

        if id_sample % 10 == 0:
            print('Generating fringe sample %i/%i' % (id_sample, N_samples))

        # creation of a sample
        my_idx_sample = np.arange(id_sample, N_images, N_samples).astype(int) 

        sample = np.zeros((len(my_idx_sample), image_shape[0], image_shape[1]))

        for i, idx in enumerate(my_idx_sample):
            # gets the image
            fringe_filename = fringe_filename_arr[idx]
            with fits.open(fringe_filename) as f:
                data_fringe = f[0].data

            # checks the size of the image
            if data_fringe.shape != image_shape:
                print('%s != %s' % (str(data_fringe.shape), str(image_shape)))
                print('** ALL IMAGES MUST BE THE SAME SIZE **')
                print('** EXITING **')
                sys.exit(0)

            # generates the normalized image
            median = np.median(data_fringe)
            data_fringe -= median
            # stocking
            sample[i] = data_fringe
            del data_fringe #clear variables

        # takes the median of the sample and then put i in fringe_maps
        sample_median = np.median(sample, axis=0)
        fringe_maps.append(sample_median)
    
    return fringe_maps, N_samples

if __name__ == "__main__":
    pass