
import os
import subprocess
import asyncio
from typing import Dict, Any, Tuple
import json
import logging

logger = logging.getLogger(__name__)

class WorkflowDeployer:
    """
    Handles the generation of Docker deployment files and execution of Docker commands.
    """
    
    @staticmethod
    def generate_docker_files(workflow_data: Dict[str, Any], output_dir: str) -> None:
        """Generates Dockerfile, requirements.txt, and main.py for the workflow."""
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Generate main.py (Re-use exporter logic)
        from core.exporter import WorkflowExporter
        script_content = WorkflowExporter.generate_script(workflow_data)
        
        with open(os.path.join(output_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(script_content)
            
        # 2. Generate requirements.txt
        # Minimal requirements for the standalone script
        reqs = [
            "asyncio",
            "aiohttp", # Often needed/used
        ]
        
        # Check if we need specific providers or tools
        nodes = workflow_data.get('nodes', {})
        for node in nodes.values():
            if node.get('provider') == 'openai':
                reqs.append('openai')
            if node.get('provider') == 'anthropic':
                reqs.append('anthropic')
            if node.get('provider') == 'google_ai':
                reqs.append('google-generativeai')
        
        # Add core dependencies if the script imports them?
        # The exported script imports 'from core.workflow...' which implies the whole codebase structure.
        # This is TRICKY. The standalone script assumes it runs IN the project or has the project libraries.
        # For a TRUE standalone Docker container, we need to copy the 'core' module.
        
        with open(os.path.join(output_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(reqs))
            
        # 3. Generate Dockerfile
        dockerfile_content = """
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (e.g. git for some tools)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy local core module (This assumes we are building from the project root context)
# We will handle the context copy logic in the backend handler
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the workflow
CMD ["python", "main.py"]
"""
        with open(os.path.join(output_dir, "Dockerfile"), "w", encoding="utf-8") as f:
            f.write(dockerfile_content.strip())

    @staticmethod
    async def build_and_run(workflow_name: str, build_dir: str) -> Tuple[bool, str]:
        """
        Attempts to build and run the docker container.
        Returns (success, message).
        """
        safe_name = workflow_name.lower().replace(" ", "_").replace("-", "_")
        image_name = f"flow_{safe_name}"
        
        # Check if docker is installed
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode != 0:
                return False, "Docker is not installed or not running."
        except FileNotFoundError:
            return False, "Docker command not found on PATH."

        try:
            # Build
            logger.info(f"Building image {image_name} from {build_dir}...")
            build_process = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", image_name, ".",
                cwd=build_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await build_process.communicate()
            
            if build_process.returncode != 0:
                return False, f"Build failed: {stderr.decode()}"
            
            # Run (Detached? Or run once?)
            # For this feature, let's run it once to verify it works, or maybe just build it.
            # a "Deploy" usually means spin it up.
            
            return True, f"Image '{image_name}' built successfully. Run with: docker run -it {image_name}"
            
        except Exception as e:
            return False, str(e)
