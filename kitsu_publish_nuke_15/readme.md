# Kitsu Publisher for Nuke

This guide will help you set up the Kitsu Publisher plugin in Nuke.

## Setup Instructions

1. **Download the Plugin**:
   - Clone or download the Kitsu DCC Publisher repository from GitHub to your local machine.

2. **Copy the Plugin Files**:
   - Locate the `kitsu_publisher_nuke` folder within the downloaded repository.
   - Copy this folder to your Nuke plugins directory. This is typically found at:
     - **Windows**: `C:\Users\<YourUsername>\.nuke\`
     - **macOS**: `/Users/<YourUsername>/.nuke/`
     - **Linux**: `/home/<YourUsername>/.nuke/`

3. **Edit the `menu.py` File**:
   - Open (or create if it doesn’t exist) the `menu.py` file in your Nuke `.nuke` directory.
   - Add the following line to import the Kitsu Publisher module:
     ```python
     import kitsu_publisher_nuke
     ```

4. **Restart Nuke**:
   - Close and reopen Nuke to load the plugin.

## Usage

Once set up, you can access the Kitsu Publisher functionality directly from the Nuke menu.

---

Happy publishing on Kitsu!
