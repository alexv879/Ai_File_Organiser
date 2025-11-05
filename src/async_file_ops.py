"""
Async file operations using aiofiles for improved performance.
Provides async versions of common file operations.
"""

import asyncio
import os
import shutil
import tempfile
from typing import List, Optional, AsyncGenerator
import aiofiles
import aiofiles.os


class AsyncFileOperations:
    """Async file operations using aiofiles."""

    @staticmethod
    async def read_file(file_path: str, encoding: str = 'utf-8') -> str:
        """Read entire file asynchronously."""
        async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
            return await f.read()

    @staticmethod
    async def read_file_lines(file_path: str, encoding: str = 'utf-8') -> List[str]:
        """Read all lines from file asynchronously."""
        async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
            return await f.readlines()

    @staticmethod
    async def read_file_binary(file_path: str) -> bytes:
        """Read binary file asynchronously."""
        async with aiofiles.open(file_path, 'rb') as f:
            return await f.read()

    @staticmethod
    async def write_file(file_path: str, content: str, encoding: str = 'utf-8') -> None:
        """Write content to file asynchronously."""
        async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
            await f.write(content)

    @staticmethod
    async def write_file_binary(file_path: str, content: bytes) -> None:
        """Write binary content to file asynchronously."""
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

    @staticmethod
    async def append_file(file_path: str, content: str, encoding: str = 'utf-8') -> None:
        """Append content to file asynchronously."""
        async with aiofiles.open(file_path, 'a', encoding=encoding) as f:
            await f.write(content)

    @staticmethod
    async def file_exists(file_path: str) -> bool:
        """Check if file exists asynchronously."""
        try:
            await aiofiles.os.stat(file_path)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    async def get_file_size(file_path: str) -> int:
        """Get file size asynchronously."""
        stat = await aiofiles.os.stat(file_path)
        return stat.st_size

    @staticmethod
    async def get_file_info(file_path: str) -> os.stat_result:
        """Get file information asynchronously."""
        return await aiofiles.os.stat(file_path)

    @staticmethod
    async def copy_file(src: str, dst: str) -> None:
        """Copy file asynchronously."""
        # For now, use thread pool for shutil operations
        # In the future, could use aiofiles.shutil if available
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, shutil.copy2, src, dst)

    @staticmethod
    async def move_file(src: str, dst: str) -> None:
        """Move file asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, shutil.move, src, dst)

    @staticmethod
    async def delete_file(file_path: str) -> None:
        """Delete file asynchronously."""
        await aiofiles.os.remove(file_path)

    @staticmethod
    async def create_directory(dir_path: str, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory asynchronously.

        Args:
            dir_path: Path to create
            parents: Create parent directories (handled by os.makedirs)
            exist_ok: Don't raise error if directory exists
        """
        loop = asyncio.get_event_loop()
        # Note: parents parameter handled by os.makedirs behavior
        _ = parents  # Mark as intentionally unused
        await loop.run_in_executor(None, os.makedirs, dir_path, exist_ok)

    @staticmethod
    async def list_directory(dir_path: str) -> List[str]:
        """List directory contents asynchronously."""
        return await aiofiles.os.listdir(dir_path)

    @staticmethod
    async def is_directory(path: str) -> bool:
        """Check if path is a directory asynchronously."""
        try:
            stat = await aiofiles.os.stat(path)
            return stat.st_mode & 0o170000 == 0o040000  # S_ISDIR
        except FileNotFoundError:
            return False

    @staticmethod
    async def is_file(path: str) -> bool:
        """Check if path is a file asynchronously."""
        try:
            stat = await aiofiles.os.stat(path)
            return stat.st_mode & 0o170000 == 0o100000  # S_ISREG
        except FileNotFoundError:
            return False


class AsyncFileProcessor:
    """Async file processor for batch operations."""

    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_files_batch(self, file_paths: List[str], operation_func, *args, **kwargs):
        """Process multiple files concurrently with limited concurrency."""
        async def process_single_file(file_path: str):
            async with self.semaphore:
                return await operation_func(file_path, *args, **kwargs)

        tasks = [process_single_file(path) for path in file_paths]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def read_multiple_files(self, file_paths: List[str], encoding: str = 'utf-8') -> List:
        """Read multiple files concurrently."""
        return await self.process_files_batch(file_paths, AsyncFileOperations.read_file, encoding)

    async def get_file_sizes(self, file_paths: List[str]) -> List:
        """Get sizes of multiple files concurrently."""
        return await self.process_files_batch(file_paths, AsyncFileOperations.get_file_size)

    async def check_files_exist(self, file_paths: List[str]) -> List:
        """Check existence of multiple files concurrently."""
        return await self.process_files_batch(file_paths, AsyncFileOperations.file_exists)


class AsyncTempFileManager:
    """Async temporary file management."""

    @staticmethod
    async def create_temp_file(suffix: str = '', prefix: str = 'tmp', dir: Optional[str] = None) -> str:
        """Create a temporary file asynchronously."""
        loop = asyncio.get_event_loop()
        fd, path = await loop.run_in_executor(
            None, tempfile.mkstemp, suffix, prefix, dir
        )
        os.close(fd)  # Close the file descriptor
        return path

    @staticmethod
    async def create_temp_directory(suffix: str = '', prefix: str = 'tmp', dir: Optional[str] = None) -> str:
        """Create a temporary directory asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, tempfile.mkdtemp, suffix, prefix, dir
        )

    @staticmethod
    async def with_temp_file(content: Optional[str] = None, binary: bool = False, **kwargs) -> AsyncGenerator[str, None]:
        """Context manager for temporary file."""
        temp_path = await AsyncTempFileManager.create_temp_file(**kwargs)

        try:
            if content is not None:
                if binary:
                    await AsyncFileOperations.write_file_binary(temp_path, content.encode())
                else:
                    await AsyncFileOperations.write_file(temp_path, content)

            yield temp_path
        finally:
            # Clean up
            try:
                await AsyncFileOperations.delete_file(temp_path)
            except FileNotFoundError:
                pass  # Already deleted

    @staticmethod
    async def with_temp_directory(**kwargs) -> AsyncGenerator[str, None]:
        """Context manager for temporary directory."""
        temp_dir = await AsyncTempFileManager.create_temp_directory(**kwargs)

        try:
            yield temp_dir
        finally:
            # Clean up directory tree
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, shutil.rmtree, temp_dir, True)


class AsyncFileIterator:
    """Async file iterator for large files."""

    def __init__(self, file_path: str, chunk_size: int = 8192, encoding: str = 'utf-8'):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.encoding = encoding

    async def iterate_lines(self) -> AsyncGenerator[str, None]:
        """Iterate over file lines asynchronously."""
        async with aiofiles.open(self.file_path, 'r', encoding=self.encoding) as f:
            async for line in f:
                yield line.rstrip('\n\r')

    async def iterate_chunks(self) -> AsyncGenerator[str, None]:
        """Iterate over file in chunks asynchronously."""
        async with aiofiles.open(self.file_path, 'r', encoding=self.encoding) as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk

    async def iterate_binary_chunks(self) -> AsyncGenerator[bytes, None]:
        """Iterate over binary file in chunks asynchronously."""
        async with aiofiles.open(self.file_path, 'rb') as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk


# Convenience functions
async def read_file_async(file_path: str, encoding: str = 'utf-8') -> str:
    """Convenience function to read a file asynchronously."""
    return await AsyncFileOperations.read_file(file_path, encoding)


async def write_file_async(file_path: str, content: str, encoding: str = 'utf-8') -> None:
    """Convenience function to write a file asynchronously."""
    return await AsyncFileOperations.write_file(file_path, content, encoding)


async def file_exists_async(file_path: str) -> bool:
    """Convenience function to check if file exists asynchronously."""
    return await AsyncFileOperations.file_exists(file_path)