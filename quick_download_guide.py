#!/usr/bin/env python3
"""
Quick guide to download all attachments from periodicals@ukragroconsult.org
"""

def print_gmail_search_commands():
    """Print Gmail search commands for downloading attachments"""

    print("📧 DOWNLOAD ALL ATTACHMENTS FROM periodicals@ukragroconsult.org")
    print("=" * 65)
    print()

    print("🔍 STEP 1: Copy these Gmail search commands")
    print("-" * 45)

    commands = [
        "from:periodicals@ukragroconsult.org has:attachment",
        "from:periodicals@ukragroconsult.org has:attachment filename:xlsx",
        "from:periodicals@ukragroconsult.org has:attachment filename:xls",
        "from:periodicals@ukragroconsult.org newer_than:30d",
        "from:periodicals@ukragroconsult.org newer_than:90d",
        "from:periodicals@ukragroconsult.org newer_than:365d",
        "from:ukragroconsult.org has:attachment",
    ]

    for i, cmd in enumerate(commands, 1):
        print(f"{i}. {cmd}")

    print()
    print("📥 STEP 2: Manual Download Process")
    print("-" * 35)
    print("1. Open Gmail in your browser")
    print("2. Copy and paste the FIRST search command above")
    print("3. Press Enter to search")
    print("4. You'll see all emails with attachments from UkrAgroConsult")
    print("5. Open each email and download ALL attachments (📎)")
    print("6. Save Excel files (.xlsx, .xls) to this folder:")
    print(f"   📁 market_data/ukragro_downloads/")
    print()

    print("⚡ QUICK TIP:")
    print("Start with: from:periodicals@ukragroconsult.org has:attachment")
    print("This will show ALL emails with any attachments.")
    print()

    print("📊 STEP 3: After downloading")
    print("-" * 30)
    print("1. Run: streamlit run app.py")
    print("2. Go to '📊 Market Intel' tab")
    print("3. Use '📤 Upload Daily Prices' to process your files")
    print()

    print("🔧 STEP 4: Verify downloads")
    print("-" * 28)
    print("Run: python check_downloads.py")
    print("(This will verify your files are ready for processing)")

def create_download_folder():
    """Create download folder"""
    from pathlib import Path

    download_dir = Path(__file__).parent / "market_data" / "ukragro_downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"✅ Created download folder: {download_dir}")
    return download_dir

def main():
    """Main function"""
    print_gmail_search_commands()
    print()

    # Create download folder
    download_dir = create_download_folder()

    print("🎯 READY TO START!")
    print("1. Use the Gmail search commands above")
    print("2. Download Excel files to the created folder")
    print("3. Process in Market Intelligence")

    # Check if any files already exist
    try:
        import os
        excel_files = []
        for file in os.listdir(download_dir):
            if file.endswith(('.xlsx', '.xls')):
                excel_files.append(file)

        if excel_files:
            print(f"\n📁 Found {len(excel_files)} existing Excel files:")
            for file in excel_files[:5]:  # Show first 5
                print(f"   - {file}")
            if len(excel_files) > 5:
                print(f"   ... and {len(excel_files) - 5} more")
        else:
            print(f"\n📂 Download folder is empty - ready for new downloads")

    except Exception as e:
        print(f"\n📁 Download folder created: {download_dir}")

if __name__ == "__main__":
    main()