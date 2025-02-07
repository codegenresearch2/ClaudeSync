import unittest\\\\nimport os\\\nimport tempfile\\\nimport logging\\\nfrom claudesync.utils import (\\n    compute_md5_hash,\\\n    load_gitignore,\\\n    get_local_files,\\\n    load_claudeignore\\n)\\\n\\\\\nlogger = logging.getLogger(__name__)\\\n\\\\nclass TestUtils(unittest.TestCase):\\\\\\\n\\\\n    def test_calculate_checksum(self):\\\\\\\n        content = "Hello, World!"\\\\\\\n        expected_checksum = "65a8e27d8879283831b664bd8b7f0ad4"\\\\\\\n        self.assertEqual(compute_md5_hash(content), expected_checksum)\\\\\\\n\\\\n    def test_load_gitignore(self):\\\\\\\n        with tempfile.TemporaryDirectory() as tmpdir:\\\\\\\n            gitignore_content = "*.log\n/node_modules\n"\\\\\\\n            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:\\\\\\\n                f.write(gitignore_content)\\\\\\\n\\\\n            gitignore = load_gitignore(tmpdir)\\\\\\\n            self.assertIsNotNone(gitignore)\\\\\\\n            self.assertTrue(gitignore.match_file("test.log"))\\\\\\\n            self.assertTrue(gitignore.match_file("node_modules/package.json"))\\\\\\\n            self.assertFalse(gitignore.match_file("src/main.py"))\\\\\\\n\\\\n    def test_get_local_files(self):\\\\\\\n        with tempfile.TemporaryDirectory() as tmpdir:\\\\\\\n            # Create some test files\\\\\\\n            with open(os.path.join(tmpdir, "file1.txt"), "w") as f:\\\\\\\n                f.write("Content of file1")\\\\\\\n            with open(os.path.join(tmpdir, "file2.py"), "w") as f:\\\\\\\n                f.write("print('Hello, World!')")\\\\\\\n            os.mkdir(os.path.join(tmpdir, "subdir"))\\\\\\\n            with open(os.path.join(tmpdir, "subdir/file3.txt"), "w") as f:\\\\\\\n                f.write("Content of file3")\\\\\\\n\\\\n            # Create a test~ file\\\\\\\n            for vcs in {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS"}:\\\\\\\n                os.mkdir(os.path.join(tmpdir, vcs))\\\\\\\n                with open(os.path.join(tmpdir, vcs, "test~"), "w") as f:\\\\\\\n                    f.write("*.log\n")\\\\\\\n\\\\n            for buildDir in {"target", "build"}:\\\\\\\n                os.mkdir(os.path.join(tmpdir, buildDir))\\\\\\\n                with open(os.path.join(tmpdir, buildDir, "output.txt"), "w") as f:\\\\\\\n                    f.write("Build output")\\\\\\\n\\\\n            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:\\\\\\\n                f.write("*.log\n/build\ntarget")\\\\\\\n\\\\n            local_files = get_local_files(tmpdir)\\\\\\\n            print(local_files)\\\\\\\n\\\\n            self.assertIn("file1.txt", local_files)\\\\\\\n            self.assertIn("file2.py", local_files)\\\\\\\n            self.assertIn(os.path.join("subdir", "file3.txt"), local_files)\\\\\\\n            self.assertNotIn(os.path.join("target", "output.txt"), local_files)\\\\\\\n            self.assertNotIn(os.path.join("build", "output.txt"), local_files)\\\\\\\n            # Ensure ignored files not included\\\\\\\n            self.assertEqual(len(local_files), 4)\\\\\\\n\\\\n    def test_load_claudeignore(self):\\\\\\\n        with tempfile.TemporaryDirectory() as tmpdir:\\\\\\\n            claudeignore_content = "*.log\n/build/"\\\\\\\n            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:\\\\\\\n                f.write(claudeignore_content)\\\\\\\n\\\\n            claudeignore = load_claudeignore(tmpdir)\\\\\\\n            self.assertIsNotNone(claudeignore)\\\\\\\n            self.assertTrue(claudeignore.match_file("test.log"))\\\\\\\n            self.assertTrue(claudeignore.match_file("build/output.txt"))\\\\\\\n            self.assertFalse(claudeignore.match_file("src/main.py"))\\\\\\\n\\\\n    def test_get_local_files_with_claudeignore(self):\\\\\\\n        with tempfile.TemporaryDirectory() as tmpdir:\\\\\\\n            # Create some test files\\\\\\\n            with open(os.path.join(tmpdir, "file1.txt"), "w") as f:\\\\\\\n                f.write("Content of file1")\\\\\\\n            with open(os.path.join(tmpdir, "file2.log"), "w") as f:\\\\\\\n                f.write("Log content")\\\\\\\n            os.mkdir(os.path.join(tmpdir, "build"))\\\\\\\n            with open(os.path.join(tmpdir, "build/output.txt"), "w") as f:\\\\\\\n                f.write("Build output")\\\\\\\n\\\\n            # Create a .claudeignore file\\\\\\\n            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:\\\\\\\n                f.write("*.log\n/build/")\\\\\\\n\\\\n            local_files = get_local_files(tmpdir)\\\\\\\n            print(local_files)\\\\\\\n\\\\n            self.assertIn("file1.txt", local_files)\\\\\\\n            self.assertNotIn("file2.log", local_files)\\\\\\\n            self.assertNotIn(os.path.join("build", "output.txt"), local_files)\\\\\\\n\\\\nif __name__ == "__main__":\\\\\\\n    unittest.main()\\\\n