# Git Workflow Guide for DARALEX P&L

## 🚀 **Setup Complete!**

✅ **Repository cloned**: `daralex-pnl` from GitHub
✅ **Git credentials configured**: Alexei Camenscic <alexei@daralex.com>
✅ **Dependencies installed**: Streamlit 1.29.0, Requests 2.31.0
✅ **App tested locally**: Running successfully on port 8501

## 📁 **Project Structure**

```
📦 daralex-pnl/
├── 📄 app.py              # Main Streamlit application (525 lines)
├── 📄 requirements.txt    # Dependencies (streamlit, requests)
├── 📄 README.md          # Project documentation
├── 📄 .gitignore         # Git ignore patterns
└── 📁 .git/              # Git repository data
```

## 🔧 **Local Development Workflow**

### **1. Open Project in PyCharm**

```bash
# Navigate to project directory
cd /Users/alexeicamenscic/PycharmProjects/PythonProject/HubSpot/daralex-pnl

# Open in PyCharm
pycharm .
# OR open PyCharm manually and select this folder
```

### **2. Test App Locally**

```bash
# Run the Streamlit app
streamlit run app.py

# App will open in browser at: http://localhost:8501
# You can edit app.py and see changes in real-time (hot reload)
```

### **3. Make Changes in PyCharm**

- Edit `app.py` in PyCharm
- Save changes (⌘+S)
- Streamlit auto-reloads in browser
- Test your changes immediately

## 📤 **Git Workflow for Deploying Changes**

### **Method 1: Command Line Git**

```bash
# 1. Check what files changed
git status

# 2. Add your changes
git add app.py                    # Add specific file
git add .                         # OR add all changes

# 3. Commit with descriptive message
git commit -m "Add new calculation feature"
git commit -m "Fix VAT calculation bug"
git commit -m "Update UI for mobile devices"

# 4. Push to GitHub (triggers Streamlit deploy)
git push origin main
```

### **Method 2: PyCharm Git Integration**

1. **View Changes**: In PyCharm, go to `View` → `Tool Windows` → `Git`
2. **Commit**: Right-click files → `Git` → `Add` → `Commit`
3. **Write Message**: Enter descriptive commit message
4. **Push**: Click `Push` button or `VCS` → `Git` → `Push`

### **Method 3: PyCharm GUI Workflow**

1. **Commit Tab**: Bottom of PyCharm window
2. **Select Files**: Check boxes for files to commit
3. **Commit Message**: Write clear description
4. **Commit and Push**: Click dropdown → "Commit and Push"

## 🌐 **Streamlit Deployment**

### **Auto-Deploy Setup**

Your Streamlit app will automatically deploy when you push to GitHub if:

1. **Connected to Streamlit Cloud**: Link your GitHub repo to Streamlit
2. **Main branch**: Pushes to `main` branch trigger deploys
3. **requirements.txt**: Dependencies are automatically installed

### **Streamlit Cloud Setup Steps**

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your GitHub account
3. Select repository: `alexeicam/daralex-pnl`
4. Set main file: `app.py`
5. Deploy!

### **Deployment URL**

After setup, your app will be available at:
```
https://alexeicam-daralex-pnl-app-[hash].streamlit.app
```

## ⚡ **Quick Development Cycle**

### **Typical Workflow:**

1. **Edit in PyCharm**: Make changes to `app.py`
2. **Test Locally**: `streamlit run app.py` → Check at http://localhost:8501
3. **Commit & Push**:
   ```bash
   git add app.py
   git commit -m "Descriptive message"
   git push origin main
   ```
4. **Auto-Deploy**: Streamlit Cloud detects push and redeploys
5. **Live in ~2 minutes**: Changes are live on your public URL

## 📝 **Best Commit Message Examples**

```bash
# Feature additions
git commit -m "Add Romanian language support"
git commit -m "Implement auto exchange rate fetching"
git commit -m "Add export to PDF functionality"

# Bug fixes
git commit -m "Fix margin calculation for high VAT rates"
git commit -m "Resolve mobile layout issues"
git commit -m "Fix currency conversion rounding"

# UI improvements
git commit -m "Improve input validation and error messages"
git commit -m "Update color scheme and branding"
git commit -m "Add tooltips for calculation parameters"

# Performance
git commit -m "Optimize API calls for exchange rates"
git commit -m "Add caching for repeated calculations"
```

## 🔍 **Useful Git Commands**

```bash
# Check repository status
git status

# View commit history
git log --oneline

# See what changed
git diff

# Undo last commit (keeps changes)
git reset --soft HEAD~1

# Pull latest changes
git pull origin main

# Create new branch for features
git checkout -b feature-name
git push -u origin feature-name
```

## 🛠️ **PyCharm Git Configuration**

### **Enable Version Control**

1. `VCS` → `Enable Version Control Integration`
2. Select `Git` as VCS
3. PyCharm will detect your `.git` folder

### **Set Up GitHub Integration**

1. `File` → `Settings` → `Version Control` → `GitHub`
2. Add account with your GitHub credentials
3. Test connection

### **Useful PyCharm Git Features**

- **File Colors**: Modified files show in blue, new files in green
- **Git Blame**: Right-click line → `Git` → `Annotate with Git Blame`
- **Compare Branches**: `VCS` → `Git` → `Compare with Branch`
- **Git History**: Right-click file → `Git` → `Show History`

## 🚨 **Important Notes**

### **Never Commit These:**

- API keys or secrets
- Large files (>100MB)
- Personal data
- Database dumps
- `.env` files with credentials

### **Always Test Before Push:**

```bash
# Test locally first
streamlit run app.py

# Check that app works completely
# Test all calculation modes
# Verify UI looks correct
```

### **Environment Variables (if needed):**

If you need API keys, use Streamlit Secrets:

```python
# In app.py
import streamlit as st

# Access secrets
api_key = st.secrets["API_KEY"]
```

And add to Streamlit Cloud → App Settings → Secrets:
```toml
API_KEY = "your-api-key-here"
```

## 🎯 **Ready to Code!**

**Your development environment is fully set up:**

1. **Edit**: Open PyCharm → Edit `app.py`
2. **Test**: Run `streamlit run app.py`
3. **Deploy**: `git add` → `git commit` → `git push`
4. **Live**: Auto-deploys to Streamlit Cloud

**Project location**: `/Users/alexeicamenscic/PycharmProjects/PythonProject/HubSpot/daralex-pnl/`

Happy coding! 🚀