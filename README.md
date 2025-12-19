# Rootics

<table>
<tr>
<td width="70%">

**Semi-Automated Data Analysis for Electrochemical Microsensors**

A graphical user interface (GUI) designed to streamline the analysis of sediment profiles measured by Unisense electrochemical microsensors. Rootics automates repetitive data preparation tasks, improves reproducibility, and enables efficient comparison of multiple profiles.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)]()

</td>
<td width="30%">
   
<img width="5090" height="5383" alt="logo_v3" src="https://github.com/user-attachments/assets/e472c446-ecf5-48ae-bdaa-4a072a142a3d" />

</td>
</tr>
</table>


## Key Features

- **Multi-Parameter Support**: Analyze O₂, pH, H₂S (total sulfide), and EP sensor profiles
- **Automated Interface Detection**: Automatic identification of sediment-water interface based on O₂ inflection points
- **Sensor Drift Correction**: Built-in correction for EP sensors using linear or 2nd-order polynomial fitting
- **Batch Processing**: Analyze multiple profiles from the same group simultaneously
- **Manual Quality Control**: Mark outliers and trim data to regions of interest
- **Enhanced Reproducibility**: Standardized workflows ensure consistent analysis across datasets


## Prerequisites

### System Requirements
- **Windows**: Version 11 or higher
- **macOS**: Version 13 (Ventura) or higher

### Knowledge Requirements
- Basic understanding of electrochemical microsensor theory
- Familiarity with sediment biogeochemistry (recommended)
- No programming knowledge required



## Installation

### Option 1: Run from Source (Recommended for Developers)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/rootics.git
   cd rootics
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download the pictures folder**
   - Ensure the `pictures/` folder is in the same directory as `Rootics.py`
   - If icons don't display, verify the path in `Rootics.py` points to this folder

4. **Run the application**
   ```bash
   python Rootics.py
   ```

### Option 2: Standalone Executable

Due to GitHub's file size limitations, the packaged executables are not available for direct download. 

**Request installation files**: Contact [info@silviazieger.com](mailto:info@silviazieger.com) for:
- Windows installer (.exe)
- macOS application bundle (.app)

---

## Quick Start Guide

### 1. Launch Rootics
- **Windows**: Double-click `Rootics.exe` or run `python Rootics.py`
- **macOS**: Open `Rootics.app` or run `python Rootics.py`

### 2. Load Your Data
- Import Unisense sensor output files
- Rootics automatically groups profiles from the same measurement session

### 3. Configure Analysis
- Select sensor type (O₂, pH, H₂S, EP)
- Choose analysis parameters:
  - Interface detection method (for O₂)
  - Drift correction type (for EP: linear or polynomial)

### 4. Quality Control
- Review automated interface detection
- Mark outliers manually if needed
- Trim data to depth range of interest

### 5. Export Results
- Save processed profiles
- Export figures for publication
- Generate summary statistics

---

## Supported Sensors
The software is generally made for electrochemical sensors from Unisense 

| Sensor Type | Parameters Measured | Automated Features |
|-------------|---------------------|-------------------|
| **O₂** | Dissolved oxygen concentration | Automatic interface detection via inflection point |
| **pH** | pH value | Profile grouping and visualization |
| **H₂S** | Hydrogen sulfide / Total sulfide | Profile grouping and visualization |
| **EP** | Redox potential | Linear or polynomial drift correction |

---

## Troubleshooting

### Icons/Pictures Not Displaying
**Problem**: GUI shows missing icons or blank image areas

**Solution**: 
1. Verify the `pictures/` folder is in the same directory as `Rootics.py`
2. Open `Rootics.py` and check the path variable (usually near the top of the file)
3. Update the path to point to your `pictures/` folder location

```python
# Example path correction in Rootics.py
PICTURES_PATH = os.path.join(os.path.dirname(__file__), 'pictures')
```

### Import Errors
**Problem**: Missing Python packages when running from source

**Solution**: Install all dependencies
```bash
pip install -r requirements.txt
```

### Data Not Loading
**Problem**: Sensor files not recognized

**Solution**: 
- Ensure files are in Unisense output format
- Check file extensions match expected format (.txt, .csv)
- Verify files are not corrupted

---

## Documentation

Please reach out for detailed information about:
- Data file formats and specifications
- Analysis algorithms and methodologies  
- Advanced configuration options
- Example workflows and use cases

---

## Contributing

Contributions, bug reports, and feature requests are welcome!

1. **Report bugs**: Open an issue with detailed description and steps to reproduce
2. **Request features**: Describe your use case and proposed functionality
3. **Submit code**: Fork the repository and submit a pull request

---

## License

Copyright © 2021 Silvia E. Zieger. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND**, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Contact & Support

**Developer**: Silvia E. Zieger  
**Email**: [info@silviazieger.com](mailto:info@silviazieger.com)  
**Issues**: [GitHub Issues](../../issues)

---

## Acknowledgments

- Unisense A/S for microsensor technology
- Research collaborators who tested and provided feedback
- The scientific community for valuable input on feature development

---

## Citation

If you use Rootics in your research, please cite:

```bibtex
@software{rootics2021,
  author = {Zieger, Silvia E.},
  title = {Rootics: GUI for Semi-Automated Data Preparation for Electrochemical Microsensors},
  year = {2021},
  url = {https://github.com/yourusername/rootics}
}
```

---

<p align="center">
  <sub>Built with ❤️ for the marine biogeochemistry community</sub>
</p>
