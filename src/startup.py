# -*- coding: utf-8 -*-
"""
Startup housekeeping helpers.

This module provides utilities to prepare the workspace before executing the main flow.
"""

import os


def initializer():
    """
    Prepare the local workspace by cleaning predefined folders.
    """

    folder = "link_status"

    if not os.path.exists(folder):
        print(f"Folder does not exist: {folder}")

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted: {file_path}")
            except Exception as e:
                print(f"❌ Error deleting {file_path}: {e}")
        else:
            print(f"⏭️ Skipped (not a file): {file_path}")