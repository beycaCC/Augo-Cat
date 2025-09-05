# 🎮 Augo-Cat - Bongo Cat Automation Tool

A fully automatic Bongo Cat program that helps you collect treasure chests and complete typing tasks while you sleep! This tool automatically detects the game, types characters, and clicks chests every 30 minutes.

## ✨ Features

- **🤖 Fully Automated**: Runs completely hands-free
- **📝 Smart Typing**: Automatically types characters for Bongo Cat
- **🎁 Chest Collection**: Automatically finds and clicks treasure chests
- **⏰ Flexible Timing**: Choose between typing mode or chest-only mode
- **🔄 Retry System**: Automatically retries if chest isn't found
- **📊 Progress Tracking**: Shows real-time progress and statistics

## 🚀 Quick Start Guide

### Step 1: Download and Install Python

1. **Go to the official Python website**: https://www.python.org/downloads/
2. **Click "Download Python"** (it will automatically detect your operating system)
3. **Run the installer** and **IMPORTANT**: Check the box "Add Python to PATH" at the bottom
4. **Click "Install Now"** and wait for installation to complete
5. **Verify installation**: Open Command Prompt (Windows) or Terminal (Mac) and type:
   ```
   python --version
   ```
   You should see something like "Python 3.11.x" or similar.

### Step 2: Download the Augo-Cat Program

1. **Download the program files**:
   - Click the green "Code" button on this page
   - Select "Download ZIP"
   - Extract the ZIP file to `D:\Augo-Cat\` folder
   - **Important**: Make sure the folder path is exactly `D:\Augo-Cat\`

### Step 3: Install Required Dependencies

1. **Open Command Prompt** (Windows) or Terminal (Mac)
2. **Navigate to the program folder**:
   ```
   cd D:\Augo-Cat
   ```
3. **Install the required packages**:
   ```
   pip install -r requirements.txt
   ```
   Wait for all packages to install (this may take a few minutes)

### Step 4: Prepare Your Game Images

1. **Make sure you have these image files** in the program folder:
   - `chest.png` - Image of the treasure chest in Bongo Cat
   - `App_icon_on_task_bar.png` - Image of the Bongo Cat app icon on your taskbar

2. **If you don't have these images**:
   - Take screenshots of the chest and taskbar icon
   - Save them with the exact names above
   - Place them in the same folder as `main.py`

### Step 5: Run the Program

1. **Start Bongo Cat game** on your computer
2. **Open Command Prompt** and navigate to the program folder
3. **Run the program**:
   ```
   python main.py
   ```
4. **Follow the on-screen menu**:
   - Choose **Option 1** for typing mode (types characters + collects chests)
   - Choose **Option 2** for chest-only mode (only collects chests)

## 🎯 How to Use

### Menu Options

When you run the program, you'll see a menu like this:

```
============================================================
🎮 BONGO CAT AUTOMATION TOOL
============================================================
Choose your operation:

1. 📝 TYPING MODE
   - Specify number of cycles to run
   - Automatically calculates characters needed (cycles × 1000)
   - Continuously types until target is reached
   - Clicks chest every 30 minutes

2. 🎯 CHEST-ONLY MODE
   - Only clicks chest every 30 minutes
   - No typing involved
   - Perfect for passive monitoring

============================================================
Your choice: 
```

### Typing Mode (Option 1)

1. **Enter the number of cycles** you want to run
2. **The program calculates** total characters needed (cycles × 1000)
3. **Confirm your choice** by typing 'y'
4. **The program will**:
   - Find and click the Bongo Cat taskbar icon
   - Type characters automatically
   - Click chests every 30 minutes
   - Show progress updates

### Chest-Only Mode (Option 2)

1. **Select this option** if you only want chest collection
2. **The program will**:
   - Find and click the Bongo Cat taskbar icon
   - Wait 30 minutes between chest clicks
   - No typing involved

## ⚙️ Troubleshooting

### Common Issues

**❌ "Python is not recognized"**
- **Solution**: Python wasn't added to PATH during installation
- **Fix**: Reinstall Python and make sure to check "Add Python to PATH"

**❌ "Missing required packages"**
- **Solution**: Run `pip install -r requirements.txt` again
- **Fix**: Make sure you're in the correct folder

**❌ "Bongo Cat not detected"**
- **Solution**: Make sure Bongo Cat game is running
- **Fix**: Start the game before running the program

**❌ "Chest not found"**
- **Solution**: The program will automatically retry 7 times over 30 minutes
- **Fix**: Check if your `chest.png` image is correct

**❌ "Taskbar icon not found"**
- **Solution**: Make sure `App_icon_on_task_bar.png` is in the program folder
- **Fix**: Take a new screenshot of the taskbar icon

### Getting Help

If you encounter issues:

1. **Check the error messages** - they usually tell you what's wrong
2. **Make sure all files are in the same folder**:
   - `main.py`
   - `requirements.txt`
   - `chest.png`
   - `App_icon_on_task_bar.png`
3. **Restart the program** if it gets stuck
4. **Check that Bongo Cat is running** before starting the program

## 📁 File Structure

```
D:\Augo-Cat\
├── main.py                          # Main program file
├── requirements.txt                 # Required Python packages
├── chest.png                       # Chest template image
├── App_icon_on_task_bar.png        # Taskbar icon template
├── .gitignore                      # Git ignore file
├── README.md                       # This instruction file
└── screenshot/                     # Screenshots folder (auto-created)
    └── (screenshots are saved here automatically)
```

## 🔧 Advanced Settings

### Customizing Character Count

- **Default**: 1000 characters per cycle
- **To change**: Edit the code in `main.py` (line with `chars_this_cycle = min(1000, remaining_chars)`)

### Adjusting Retry Settings

- **Default**: 7 attempts over 30 minutes
- **To change**: Edit `max_attempts=7` in the `take_screenshot_and_find_chest` function

### Changing Wait Times

- **Default**: 5 minutes between retries
- **To change**: Edit the `range(300, 0, -1)` line (300 = 5 minutes in seconds)

## 🎉 Success Tips

1. **Test first**: Run a short test with 1-2 cycles before long runs
2. **Keep Bongo Cat visible**: Don't minimize the game window
3. **Stable internet**: Make sure your connection is stable
4. **Monitor initially**: Watch the first few cycles to ensure everything works
5. **Save screenshots**: The program saves screenshots for debugging

## ⚠️ Important Notes

- **This program is for educational purposes only**
- **Use responsibly** and in accordance with game terms of service
- **The program requires the game to be running** and visible
- **Screenshots are automatically saved** for debugging purposes
- **You can stop the program anytime** with Ctrl+C

## 🆘 Emergency Stop

If you need to stop the program immediately:
1. **Press Ctrl+C** in the command prompt
2. **The program will stop** and show a summary of what was completed
3. **No data will be lost** - you can restart anytime

---

**Happy Gaming! 🎮✨**

*Enjoy your automated Bongo Cat experience and collect those treasure chests!*