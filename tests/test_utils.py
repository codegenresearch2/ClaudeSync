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
        self.assertEqual(compute_md5_hash(content), expected_checksum)

    def test_load_gitignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_content = "*.log\n/node_modules\n"
            gitignore_path = os.path.join(tmpdir, ".gitignore")
            with open(gitignore_path, "w") as f:
                f.write(gitignore_content)

            gitignore = load_gitignore(tmpdir)
            self.assertIsNotNone(gitignore)
            self.assertTrue(gitignore.match_file("test.log"))
            self.assertTrue(gitignore.match_file("node_modules/package.json"))
            self.assertFalse(gitignore.match_file("src/main.py"))

    def test_get_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            file1_path = os.path.join(tmpdir, "file1.txt")
            with open(file1_path, "w") as f:
                f.write("Content of file1")
            file2_path = os.path.join(tmpdir, "file2.py")
            with open(file2_path, "w") as f:
                f.write("print('Hello, World!')")
            subdir_path = os.path.join(tmpdir, "subdir")
            os.mkdir(subdir_path)
            file3_path = os.path.join(subdir_path, "file3.txt")
            with open(file3_path, "w") as f:
                f.write("Content of file3")

            # Create a test~ file directly in the temporary directory
            test_tilde_path = os.path.join(tmpdir, "test~")
            with open(test_tilde_path, "w") as f:
                f.write("*.log\n")

            # Include the specific version control system directories
            for vcs in {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS", "claude_chats"}:
                vcs_path = os.path.join(tmpdir, vcs)
                os.mkdir(vcs_path)

            for buildDir in {"target", "build"}:
                build_dir_path = os.path.join(tmpdir, buildDir)
                os.mkdir(build_dir_path)
                build_output_path = os.path.join(build_dir_path, "output.txt")
                with open(build_output_path, "w") as f:
                    f.write("Build output")

            gitignore_path = os.path.join(tmpdir, ".gitignore")
            with open(gitignore_path, "w") as f:
                f.write("*.log\n/build\ntarget")

            claudeignore_path = os.path.join(tmpdir, ".claudeignore")
            with open(claudeignore_path, "w") as f:
                f.write("*.log\n/build/\n")

            local_files = get_local_files(tmpdir)
            self.assertEqual(len(local_files), 4)  # Expected number of local files

    def test_load_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            claudeignore_content = "*.log\n/build/\n"
            claudeignore_path = os.path.join(tmpdir, ".claudeignore")
            with open(claudeignore_path, "w") as f:
                f.write(claudeignore_content)

            claudeignore = load_claudeignore(tmpdir)
            self.assertIsNotNone(claudeignore)
            self.assertTrue(claudeignore.match_file("test.log"))
            self.assertTrue(claudeignore.match_file("build/output.txt"))
            self.assertFalse(claudeignore.match_file("src/main.py"))

    def test_get_local_files_with_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            file1_path = os.path.join(tmpdir, "file1.txt")
            with open(file1_path, "w") as f:
                f.write("Content of file1")
            file2_log_path = os.path.join(tmpdir, "file2.log")
            with open(file2_log_path, "w") as f:
                f.write("Log content")
            build_path = os.path.join(tmpdir, "build")
            os.mkdir(build_path)
            build_output_path = os.path.join(build_path, "output.txt")
            with open(build_output_path, "w") as f:
                f.write("Build output")

            # Create a .claudeignore file
            claudeignore_path = os.path.join(tmpdir, ".claudeignore")
            with open(claudeignore_path, "w") as f:
                f.write("*.log\n/build/\n")

            local_files = get_local_files(tmpdir)
            self.assertEqual(len(local_files), 3)  # Expected number of local files

if __name__ == "__main__":
    unittest.main()