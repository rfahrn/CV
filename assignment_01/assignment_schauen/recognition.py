import os
import numpy as np
import cv2
import matplotlib.pyplot as plt

from tqdm.notebook import tqdm

from utils import read_image, show_image
from frontalization import rescale_image, frontalize_image

# BEGIN YOUR IMPORTS

# END YOUR IMPORTS

NUM_CELLS = 9
CELL_SIZE = (64, 64)
SUDOKU_SIZE = (CELL_SIZE[0]*NUM_CELLS, CELL_SIZE[1]*NUM_CELLS)

TEMPLATES_PATH = os.path.join(".", "templates")


def resize_image(image, size):
    """
    Args:
        image (np.array): input image of shape [H, W]
        size (int, int): desired image size
    Returns:
        resized_image (np.array): 8-bit (with range [0, 255]) resized image
    """
    # BEGIN YOUR CODE

    resized_image = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    
    
    # END YOUR CODE

    return resized_image


def binarize(image, **binarization_kwargs):
    """
    Args:
        image (np.array): input image
        binarization_kwargs (dict): dict of parameter values
    Returns:
        binarized_image (np.array): binarized image

    You can find information about different thresholding algorithms here
    https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html
    """
    # BEGIN YOUR CODE

    binarized_image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, **binarization_kwargs)
    # END YOUR CODE
    
    return binarized_image


def crop_image(image, crop_factor):
    size = image.shape[:2]
    
    cropped_size = (int(size[0]*crop_factor), int(size[1]*crop_factor))
    shift = ((size[0] - cropped_size[0]) // 2, (size[1] - cropped_size[1]) // 2)

    cropped_image = image[shift[0]:shift[0]+cropped_size[0],
                          shift[1]:shift[1]+cropped_size[1]]

    return cropped_image


def get_sudoku_cells(frontalized_image, crop_factor=0.8, binarization_kwargs={'blockSize': 11, 'C': 2}):
    """
    Args:
        frontalized_image (np.array): frontalized sudoku image
        crop_factor (float): how much cell area we should preserve
        binarization_kwargs (dict): dict of parameter values for the binarization function
    Returns:
        sudoku_cells (np.array): array of num_cells x num_cells sudoku cells of shape [N, N, S, S]
    """
    # BEGIN YOUR CODE

    resized_image = resize_image(frontalized_image, SUDOKU_SIZE) 
    binarized_image = binarize(resized_image, **binarization_kwargs)
    
    
    sudoku_cells = np.zeros((NUM_CELLS, NUM_CELLS, *CELL_SIZE), dtype=np.uint8)
    cell_dim = SUDOKU_SIZE[0] // NUM_CELLS

    for i in range(NUM_CELLS):
        for j in range(NUM_CELLS):
            sudoku_cell = binarized_image[i*cell_dim:(i+1)*cell_dim, j*cell_dim:(j+1)*cell_dim]
            sudoku_cell = crop_image(sudoku_cell, crop_factor=crop_factor)
            
            sudoku_cells[i, j] = resize_image(sudoku_cell, CELL_SIZE)

    # END YOUR CODE

    return sudoku_cells


def load_templates():
    """
    Returns:
        templates (dict): dict with digits as keys and lists of template images (np.array) as values
    """
    templates = {}
    for folder_name in sorted(os.listdir(TEMPLATES_PATH)):
        if "." in folder_name:
            continue
        
        folder_path = os.path.join(TEMPLATES_PATH, folder_name)
        templates[int(folder_name)] = [read_image(os.path.join(folder_path, file_name))
                                       for file_name in sorted(os.listdir(folder_path))]
    
    return templates


def is_empty(sudoku_cell, **kwargs):
    """
    Args:
        sudoku_cell (np.array): image (np.array) of a Sudoku cell
        kwargs (dict): dict of parameter values for this function
    Returns:
        cell_is_empty (bool): True or False depends on whether the Sudoku cell is empty or not
    """
    # BEGIN YOUR CODE
    sum_of_values = np.sum(sudoku_cell)
    threshold = kwargs.get('threshold', 1000)  # calibrate this threshold as per of data
    cell_is_empty = sum_of_values < threshold
    # END YOUR CODE

    return cell_is_empty


def get_digit_correlations(sudoku_cell, templates_dict):
    """
    Args:
        sudoku_cell (np.array): image (np.array) of a Sudoku cell
        templates_dict (dict): dict with digits as keys and lists of template images (np.array) as values
    Returns:
        correlations (np.array): an array of correlation coefficients between Sudoku cell and digit templates
    """
    correlations = np.zeros(9)
    
    if is_empty(sudoku_cell, threshold=1000):
        return correlations
    
    # BEGIN YOUR CODE

    for digit, templates in templates_dict.items():
        for template in templates:  # Iterate over each template
                correlation = cv2.matchTemplate(sudoku_cell, template, cv2.TM_CCOEFF_NORMED)
                correlations[digit - 1] = max(correlations[digit - 1], np.max(correlation))

    # END YOUR CODE

    return correlations


def show_correlations(sudoku_cell, correlations):
    figure, axes = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
    
    show_image(sudoku_cell, axis=axes[0], as_gray=True)
    
    colors = ['blue' if value < np.max(correlations) else 'red' for value in correlations]
    axes[1].bar(np.arange(1, 10), correlations, tick_label=np.arange(1, 10), color=colors)
    axes[1].set_title("Correlations")


def recognize_digits(sudoku_cells, templates_dict, threshold=0.5):
    """
    Args:
        sudoku_cells (np.array): np.array of the Sudoku cells of shape [N, N, S, S]
        templates_dict (dict): dict with digits as keys and lists of template images (np.array) as values
        threshold (float): empty cell detection threshold
    Returns:
        sudoku_matrix (np.array): a matrix of shape [N, N] with recognized digits of the Sudoku grid
    """
    # BEGIN YOUR CODE
    
    sudoku_matrix = np.zeros(sudoku_cells.shape[:2], dtype=np.uint8)
    for i in range(sudoku_cells.shape[0]):
        for j in range(sudoku_cells.shape[1]):
            correlations = get_digit_correlations(sudoku_cells[i, j], templates_dict)
            # If the max correlation is above a certain threshold, we can assume the digit is recognized
            if np.max(correlations) > threshold:
                sudoku_matrix[i, j] = np.argmax(correlations) + 1
            else:
                sudoku_matrix[i, j] = 0  # empty cell

    # END YOUR CODE
    
    return sudoku_matrix


def show_recognized_digits(image_paths, pipeline,
                           crop_factor, binarization_kwargs,
                           figsize=(16, 12), digit_fontsize=10):
    nrows = len(image_paths) // 4 + 1
    ncols = 4
    figure, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize)
    if len(axes.shape) == 1:
        axes = axes[np.newaxis, ...]

    for j in range(len(image_paths), nrows * ncols):
        axis = axes[j // ncols][j % ncols]
        show_image(np.ones((1, 1, 3)), axis=axis)
    
    for index, image_path in enumerate(tqdm(image_paths)):
        axis = axes[index // ncols][index % ncols]
        axis.set_title(os.path.split(image_path)[1])
        
        sudoku_image = read_image(image_path=image_path)
        frontalized_image = frontalize_image(sudoku_image, pipeline)
        sudoku_cells = get_sudoku_cells(frontalized_image, crop_factor=crop_factor, binarization_kwargs=binarization_kwargs)

        templates_dict = load_templates()
        sudoku_matrix = recognize_digits(sudoku_cells, templates_dict)

        show_image(frontalized_image, axis=axis, as_gray=True)
        
        frontalized_cell_size = (frontalized_image.shape[0]//NUM_CELLS, frontalized_image.shape[1]//NUM_CELLS)
        for i in range(NUM_CELLS):
            for j in range(NUM_CELLS):
                axis.text((j + 1)*frontalized_cell_size[0] - int(0.3*frontalized_cell_size[0]),
                          i*frontalized_cell_size[1] + int(0.3*frontalized_cell_size[1]),
                          str(sudoku_matrix[i, j]), fontsize=digit_fontsize, c='r')


def show_solved_sudoku(frontalized_image, sudoku_matrix, sudoku_matrix_solved, digit_fontsize=20):
    show_image(frontalized_image, as_gray=True)

    frontalized_cell_size = (frontalized_image.shape[0]//NUM_CELLS, frontalized_image.shape[1]//NUM_CELLS)
    for i in range(NUM_CELLS):
        for j in range(NUM_CELLS):
            if sudoku_matrix[i, j] == 0:
                plt.text(j*frontalized_cell_size[0] + int(0.3*frontalized_cell_size[0]),
                         (i + 1)*frontalized_cell_size[1] - int(0.3*frontalized_cell_size[1]),
                         str(sudoku_matrix_solved[i, j]), fontsize=digit_fontsize, c='g')
