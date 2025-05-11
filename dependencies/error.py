"""
This module provides a function that supplies the HTTPException
"""

from fastapi import HTTPException

def httpError(status_code: int, detail: str) -> HTTPException:
    """
    Returns an HTTPException object in the correct api error response format.
    """
    return HTTPException(status_code=status_code, detail={"success": False, "message": detail})