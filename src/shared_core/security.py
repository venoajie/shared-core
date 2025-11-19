# core/security.py

import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(secret_name: str) -> str:
    """
    Retrieves a secret value using the recommended Docker secrets pattern.
    Priority order:
    1. Check for an environment variable ending in _FILE (e.g., MY_SECRET_FILE).
    2. Fall back to the default Docker secrets path (/run/secrets/).
    3. Fall back to a direct environment variable (e.g., MY_SECRET).
    """
    # 1. Check for a _FILE environment variable (Docker secrets standard)
    file_env_var = f"{secret_name.upper()}_FILE"
    if secret_path_from_env := os.getenv(file_env_var):
        if os.path.exists(secret_path_from_env):
            with open(secret_path_from_env, "r") as f:
                return f.read().strip()
        else:
            # This case helps debug when the compose file is right but the mount failed
            log.warning(
                f"Secret file specified by {file_env_var} not found at path: {secret_path_from_env}"
            )

    # 2. Check Docker secrets default path as a fallback
    secret_path_default = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path_default):
        with open(secret_path_default, "r") as f:
            return f.read().strip()

    # 3. Check direct environment variables
    if value := os.getenv(secret_name.upper()):
        return value

    # Handle case where env var might use underscores instead of hyphens
    if value := os.getenv(secret_name.upper().replace("-", "_")):
        return value

    # If all methods fail, raise an informative error.
    raise ValueError(f"Missing secret: '{secret_name}'. All lookup methods failed.")
