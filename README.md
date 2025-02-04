# Aurora Asset Converter

A crude Python implementation for converting images to Aurora .asset format and vice versa. This project is a Python interpretation of the original work by Swizzy and MaesterRowen.

## Features
- Convert images to Aurora .asset format
- Extract images from .asset files
- Support for multiple asset types (Icons, Banners, Boxart, Backgrounds, Screenshots)
- Command line interface for batch processing
- Automatic image resizing and compression for images

## Installation
1. Clone this repository
2. Run the setup script to create a self-contained 32-bit Python environment:
```PowerShell
.\Setup-Environment.ps1
```
3. Have fun!

## Usage


Example Titleid: 4D5308DE


### Convert background image
```bash
python convert.py background input.jpg 4D5308DE
```
Outputs BK4D5308DE.asset


### Convert banner and icon images
```bash
python convert.py bannericon --banner banner.jpg --icon icon.png 4D5308DE
```
Outputs GL4D5308DE.asset


### Convert boxart image
```bash
python convert.py boxart input.jpg 4D5308DE
```
Outputs GC4D5308DE.asset


### Convert multiple screenshots
```bash
python convert.py screenshots --screenshots screenshot1.jpg screenshot2.jpg screenshot3.jpg ... 4D5308DE
```
Outputs SS4D5308DE.asset


### Extract image from asset
```bash
python convert.py extract 4D5308DE.asset output.png
```



### Process folder of assets
```bash
python convert.py folder /path/to/assets 4D5308DE
```
Output .asset files will be placed in a subfolder named `<titleid>` within the source folder so in this example it would be `/path/to/assets/4D5308DE/`
This will use all matching images in the source folder and convert into .asset files:
* boxart.{png,jpg,webp} or boxart_001.{png,jpg,webp}
* banner.{png,jpg,webp} or banner_001.{png,jpg,webp}
* icon.{png,jpg,webp} or icon_001.{png,jpg,webp}
* background.{png,jpg,webp} or background_001.{png,jpg,webp}
* screenshot1.{png,jpg,webp}, screenshot2.{png,jpg,webp}, screenshot3.{png,jpg,webp} (no alternative _001 suffix for these)

Optional argument for folder `--overwrite` can be used to overwrite existing files .asset files in target folder.



### Available commands

- `background`: Convert background image
- `boxart`: Convert boxart image
- `screenshots`: Convert multiple screenshots
- `bannericon`: Convert banner and icon images
- `folder`: Process all assets in a folder
- `extract`: Extract image from asset file

## Credits
This project is based on the original work by:

- **Swizzy** - Creator of the Aurora Asset Editor and documentation of the .asset format
  - Original C# implementation: `AuroraAsset.cs`
  - Created: 04/05/2015
  - [GitHub](https://github.com/Swizzy)

- **MaesterRowen (Phoenix)** - Creator of the AuroraAsset.dll and technical documentation
  - DLL wrapper implementation: `AuroraAssetDll.cs`
  - Created: May 2015
  - Provided technical details about the .asset format

This Python implementation is a direct interpretation of their work, using the same AuroraAsset.dll for image conversion between D3DTexture and Bitmap formats.