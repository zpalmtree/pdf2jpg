import os
import uuid

from flask import Flask, render_template, request, redirect, flash, jsonify
from werkzeug.utils import secure_filename

from wand.image import Image as Img
from wand.exceptions import DelegateError

from PIL import Image


COMPRESSION_QUALITY = 99
IMAGE_RESOLUTION = 200


app = Flask(__name__)
app.config['SECRET_KEY'] = 'some super secret key'
app.config['UPLOAD_FOLDER'] = '/home/zach/Code/Python/pdf2jpg/uploads'


def isPDF(filename):
    return filename.endswith('.pdf') or filename.endswith('.PDF')


@app.route('/', methods=['POST'])
def upload():
    print('Got files.')

    if 'files[]' not in request.files:
        print('No files present in request!')
        flash('No files present in request!')
        return redirect(request.url)

    files = request.files.getlist("files[]")

    # No files uploaded
    if not files:
        print('No selected file!')
        flash('No selected file!')
        return redirect(request.url)

    saved = []

    for file in files:
        print('checking file')
        if not isPDF(file.filename):
            print('File does not have a .pdf extension!')
            flash('File does not have a .pdf extension!')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        saved.append({'url': 'uploads/', 'name': filename})

    response = {'files': saved}

    print(jsonify(response))

    return jsonify(response)


@app.route('/', methods=['GET'])
def hello():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()


def pdfToJpeg(inputFile, outputFile, resolution=IMAGE_RESOLUTION,
              compression=COMPRESSION_QUALITY, multipleFiles=True):
    try:
        with Img(filename=inputFile, resolution=resolution) as input:
            if input.format != 'PDF':
                raise RuntimeError('Input file is not a PDF.')

            # pages = len(input.sequence)

            input.compression_quality = compression

            if multipleFiles:
                input.save(filename=outputFile)
                return

            # Make sure we're not overwriting any existing files
            u = uuid.uuid4()

            # The API to split a file into sections and combine them natively
            # appears to not work and crash with a null insertion, so instead
            # lets reopen the written files and combine them with pillow...
            try:
                input.save(filename='{}-{}'.format(u, outputFile))

                # Sort the files so they're in order
                imageFiles = [filename for filename in os.listdir('.')
                              if filename.startswith(str(u))]
                imageFiles.sort()

                # Need to make a list as maps can only be iterated over once
                images = list(map(Image.open, imageFiles))
                widths, heights = zip(*(i.size for i in images))

                # Each image laid end to end gives us the height
                imgHeight = sum(heights)
                # And the width is the width of the largest image
                imgWidth = max(widths)

                # Make our output image
                outputImage = Image.new('RGB', (imgWidth, imgHeight))
                heightOffset = 0

                # Loop through each image, and append it to the output,
                # altering the height offset by the height of each image as we
                # go
                for image in images:
                    outputImage.paste(image, (0, heightOffset))
                    heightOffset += image.size[1]

                outputImage.save(outputFile)

            # Make sure we remove the tmp files
            finally:
                for file in imageFiles:
                    os.remove(file)

    # If the pdf is corrupt / empty, it will attempt to free the image object
    # when we exit the program, and this fails because the image object is
    # empty. This also can't be caught because it occurs when the runtime is
    # exiting, so we'll get an ugly stack trace when we quit. We can't attempt
    # to del it before exiting because this will fail, so it will again be
    # automatically called on exit.
    except DelegateError:
        raise RuntimeError('PDF file appears corrupted.')


def getInputOutputFiles():
    filename = input('PDF to open: ')
    newFilename = os.path.splitext(filename)[0] + '.jpg'

    if not os.path.isfile(filename):
        raise RuntimeError('Specified file doesn\'t exist.')

    return filename, newFilename


def confirm(msg):
    x = input('{} (Y/n): '.format(msg)).lower()
    return x == 'y' or x == '\n'


def main():
    try:
        filename, newFilename = getInputOutputFiles()

        multipleFiles = confirm('Create an image for each page?')

        pdfToJpeg(inputFile=filename, outputFile=newFilename,
                  multipleFiles=multipleFiles)

        print('Conversion successfully completed.')
    except RuntimeError as e:
        print('An error occured: {}'.format(e))
    except Exception as e:
        print('An unexpected error occured: {}'.format(e))
