# TrimAlign

A GUI tool to **automatically crop black borders** from scanned/photographed documents and **straighten the page**, designed for users who don't want to deal with command-line tools.  

## Features

- **Crops** the black border around images (typical of scans or photos of documents)
- **Detects and corrects** page rotation, so edges come out aligned
- **Batch processes** entire folders at once
- **Simple GUI**: pick input and output folders, click "Start"
- **Packaged as a single `.exe`**: end users don't need Python installed


## 🚀 Usage  

### Option A — With Python installed

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Launch the GUI:
   ```bash
   python pipeline_gui.py
   ```

3. In the window:
   - **Input folder** → where the images to process are
   - **Output folder** → where results are saved (suggested automatically)
   - Click **Start**

### Option B — Using the `.exe` (no Python required)

1. Download `TrimAlign.exe` from the [Releases](../../releases) section
2. Double-click it
3. Same procedure as Option A

## Building the executable

If you want to build the `.exe` yourself:

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --collect-all cv2 --name "TrimAlign" pipeline_gui.py
```

The executable is created at `dist/TrimAlign.exe`.

> ⚠️ On first launch, Windows SmartScreen may show a warning (the exe isn't digitally signed). Click **More info → Run anyway**.

## Parameters

All adjustable from the GUI (defaults work for most cases):

| Parameter | Default | What it does |
|---|---|---|
| **Black threshold** | 25 | How dark a pixel must be to count as "black" (0–255). Increase if a grey border remains. |
| **Noise filter** | 0.03 | Minimum fraction of light pixels for a row/column to count as "content". Increase if white specks remain on the border. |
| **Final padding** | 5 | Pixel margin kept around the content. |
| **Max rotation** | 20 | Maximum accepted rotation (in degrees). Beyond this, the image is left unchanged for safety. |

## How it works (briefly)

1. **Page detection**: Otsu threshold + `approxPolyDP` to find the document's four corners
2. **Rotation**: `warpAffine` with an expanded canvas, so nothing gets cut off
3. **Black border trim**: row/column projection with noise tolerance

## Supported formats

`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.webp`

## Requirements

- Python 3.10+
- opencv-python
- numpy
- Pillow (optional, for development)

## 📄 License

See the [LICENSE](LICENSE) file.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.


## Author

**Tiziana Pasciuto** – Conception, design, and creation.  

## Funding

Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Council Executive Agency. Neither the European Union nor the granting authority can be held responsible for them.
This work is supported by **ERC Grant REDMIX – Agreement 101124725**.

## ✉️ Contact

For questions or further information: redmix@unito.it or tiziana.pasciuto@unito.it
