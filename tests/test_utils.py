import unittest
import os
import tempfile

from claudesync.utils import (
    compute_md5_hash,
    load_gitignore,
    get_local_files,
    load_claudeignore,
)

class TestUtils(unittest.TestCase):

    def test_calculate_checksum(self):
        content = "Hello, World!"
        expected_checksum = "65a8e27d8879283831b664bd8b7f0ad4"
        self.assertEqual(compute_md5_hash(content), expected_checksum, "Checksum calculation failed")

    def test_load_gitignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_content = "*.log\n/node_modules\n"
            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write(gitignore_content)

            gitignore = load_gitignore(tmpdir)
            self.assertIsNotNone(gitignore, ".gitignore loading failed")
            self.assertTrue(gitignore.match_file("test.log"), ".gitignore pattern matching failed")

    def test_get_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = {
                "file1.txt": "Content of file1",
                "file2.py": "print('Hello, World!')",
                os.path.join("subdir", "file3.txt"): "Content of file3",
                os.path.join("target", "output.txt"): "Build output",
                os.path.join("build", "output.txt"): "Build output",
            }
            for path, content in files.items():
                os.makedirs(os.path.dirname(os.path.join(tmpdir, path)), exist_ok=True)
                with open(os.path.join(tmpdir, path), "w") as f:
                    f.write(content)

            # Create .gitignore file
            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write("*.log\n/build\ntarget")

            local_files = get_local_files(tmpdir)
            self.assertEqual(len(local_files), 3, "Incorrect number of files processed")

    def test_load_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            claudeignore_content = "*.log\n/build/\n"
            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:
                f.write(claudeignore_content)

            claudeignore = load_claudeignore(tmpdir)
            self.assertIsNotNone(claudeignore, ".claudeignore loading failed")
            self.assertTrue(claudeignore.match_file("test.log"), ".claudeignore pattern matching failed")

    def test_get_local_files_with_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = {
                "file1.txt": "Content of file1",
                "file2.log": "Log content",
                os.path.join("build", "output.txt"): "Build output",
            }
            for path, content in files.items():
                os.makedirs(os.path.dirname(os.path.join(tmpdir, path)), exist_ok=True)
                with open(os.path.join(tmpdir, path), "w") as f:
                    f.write(content)

            # Create .claudeignore file
            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:
                f.write("*.log\n/build/\n")

            local_files = get_local_files(tmpdir)
            self.assertEqual(len(local_files), 1, "Incorrect number of files processed with .claudeignore")

if __name__ == "__main__":
    unittest.main()