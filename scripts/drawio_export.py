#!/usr/bin/env python3
import os
import subprocess
import time
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class DrawioHandler(FileSystemEventHandler):
    def __init__(self, source_dir, output_dir):
        self.source_dir = source_dir
        self.output_dir = output_dir

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".drawio"):
            self.convert_drawio(event.src_path)

    def convert_drawio(self, file_path):
        try:
            filename = os.path.basename(file_path)
            output_filename = os.path.splitext(filename)[0] + ".png"
            output_path = os.path.join(self.output_dir, output_filename)

            # Try different possible drawio executable names/paths
            drawio_commands = [
                "drawio",
                "draw.io",
                "/Applications/draw.io.app/Contents/MacOS/draw.io",  # macOS path
                "~/Applications/draw.io.app/Contents/MacOS/draw.io",  # User's Applications folder
            ]

            cmd = None
            for drawio_cmd in drawio_commands:
                expanded_path = os.path.expanduser(drawio_cmd)
                if os.system(f"which {expanded_path} > /dev/null 2>&1") == 0:
                    cmd = [
                        expanded_path,
                        "--export",
                        "--format",
                        "png",
                        "--scale",
                        "2.0",
                        "--border",
                        "20",
                        "--output",
                        output_path,
                        file_path,
                    ]
                    break

            if cmd is None:
                raise FileNotFoundError(
                    "Draw.io executable not found. Please install Draw.io and ensure it's available in your PATH"
                )

            subprocess.run(cmd, check=True)
            print(
                f"Successfully converted {filename} to {output_filename} (scale: 200%, border: 20px)"
            )
        except subprocess.CalledProcessError as e:
            print(f"Error converting {filename}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")


def convert_single_file(input_file, output_dir):
    """Convert a single DrawIO file to PNG"""
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        return False

    handler = DrawioHandler(os.path.dirname(input_file), output_dir)
    handler.convert_drawio(input_file)
    return True


def watch_directory(source_dir, output_dir):
    """Watch a directory for changes"""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize event handler and observer
    event_handler = DrawioHandler(source_dir, output_dir)
    observer = Observer()
    observer.schedule(event_handler, source_dir, recursive=False)
    observer.start()

    print(f"Watching for changes in {source_dir}")
    print(f"Images will be saved to {output_dir}")
    print("Export settings: scale=200%, border=20px")
    print("Press Ctrl+C to stop...")

    try:
        # Convert existing files on startup
        for filename in os.listdir(source_dir):
            if filename.endswith(".drawio"):
                file_path = os.path.join(source_dir, filename)
                event_handler.convert_drawio(file_path)

        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping drawio export service...")

    observer.join()


def main():
    # Get the project root directory (parent of scripts directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Setup argument parser
    parser = argparse.ArgumentParser(description="Convert DrawIO files to PNG")
    parser.add_argument("--file", "-f", help="Single DrawIO file to convert")
    parser.add_argument(
        "--watch", "-w", action="store_true", help="Watch directory for changes"
    )
    args = parser.parse_args()

    # Set default directories relative to project root
    source_dir = os.path.join(project_root, "docs/Flowchart")
    output_dir = os.path.join(project_root, "docs/pictures")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    if args.file:
        # Convert single file
        input_file = os.path.abspath(args.file)
        convert_single_file(input_file, output_dir)
    elif args.watch:
        # Watch directory for changes
        watch_directory(source_dir, output_dir)
    else:
        print("Error: Please specify either --file or --watch option")
        parser.print_help()


if __name__ == "__main__":
    main()
