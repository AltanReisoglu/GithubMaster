import re

class FileFilter:
    IGNORED_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.zip', '.tar', '.gz',
        '.bin', '.obj', '.exe', '.dll', '.so', '.dylib', '.lock'
    }
    
    IGNORED_FILES = {
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
        '.gitignore', '.dockerignore'
    }
    
    IGNORED_DIRS = {
        'node_modules', 'bin', 'obj', '.git', '.idea', '.vscode', '__pycache__', 'vendor'
    }

    @classmethod
    def should_ignore(cls, file_path: str) -> bool:
        # Check extensions
        if any(file_path.lower().endswith(ext) for ext in cls.IGNORED_EXTENSIONS):
            return True
            
        # Check filenames
        filename = file_path.split('/')[-1]
        if filename in cls.IGNORED_FILES:
            return True
            
        # Check directories
        path_segments = set(file_path.split('/'))
        if not path_segments.isdisjoint(cls.IGNORED_DIRS):
            return True
            
        return False

    @classmethod
    def filter_diff(cls, diff_text: str):
        """
        Parses a git diff and extracts changes for files that are not ignored.
        Returns a list of dicts: [{'file': 'path/to/file', 'diff': 'patch content'}]
        """
        # Simple regex to split diff by file
        files = re.split(r'^diff --git ', diff_text, flags=re.MULTILINE)
        filtered_changes = []
        
        for file_diff in files:
            if not file_diff.strip():
                continue
                
            # Extract file path
            match = re.search(r'b/(.*)', file_diff)
            if match:
                file_path = match.group(1).split()[0]
                if not cls.should_ignore(file_path):
                    filtered_changes.append({
                        "file": file_path,
                        "diff": "diff --git " + file_diff
                    })
        
        return filtered_changes
