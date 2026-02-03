"""
Project Builder Tools - Comprehensive toolset for creating and managing game projects.

Provides agents with the ability to:
- Create and manage directory structures
- Install packages and dependencies
- Use external tools and programs
- Build proper project scaffolds
- Manage assets and templates
"""

import os
import json
import shutil
import subprocess
import logging
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Base directory for all game projects
PROJECTS_BASE = Path("exports/games")

# Approved package managers and their install commands
PACKAGE_MANAGERS = {
    "npm": {"install": "npm install", "init": "npm init -y", "check": "npm --version"},
    "yarn": {"install": "yarn add", "init": "yarn init -y", "check": "yarn --version"},
    "pip": {"install": "pip install", "init": None, "check": "pip --version"},
    "cargo": {"install": "cargo add", "init": "cargo init", "check": "cargo --version"},
    "pnpm": {"install": "pnpm add", "init": "pnpm init", "check": "pnpm --version"},
}

# Approved external tools that agents can request installation for
APPROVED_TOOLS = {
    # Game Engines & Frameworks
    "phaser": {"type": "npm", "package": "phaser", "description": "HTML5 game framework"},
    "pixijs": {"type": "npm", "package": "pixi.js", "description": "2D rendering engine"},
    "three": {"type": "npm", "package": "three", "description": "3D graphics library"},
    "babylon": {"type": "npm", "package": "@babylonjs/core", "description": "3D game engine"},
    "kaboom": {"type": "npm", "package": "kaboom", "description": "Simple game library"},
    "excalibur": {"type": "npm", "package": "excalibur", "description": "TypeScript game engine"},

    # Build Tools
    "vite": {"type": "npm", "package": "vite", "description": "Fast build tool"},
    "webpack": {"type": "npm", "package": "webpack webpack-cli", "description": "Module bundler"},
    "esbuild": {"type": "npm", "package": "esbuild", "description": "Fast JS bundler"},
    "parcel": {"type": "npm", "package": "parcel", "description": "Zero config bundler"},
    "rollup": {"type": "npm", "package": "rollup", "description": "ES module bundler"},

    # TypeScript & Languages
    "typescript": {"type": "npm", "package": "typescript", "description": "TypeScript compiler"},
    "ts-node": {"type": "npm", "package": "ts-node", "description": "TypeScript execution"},

    # Testing
    "jest": {"type": "npm", "package": "jest", "description": "Testing framework"},
    "vitest": {"type": "npm", "package": "vitest", "description": "Vite-native testing"},
    "playwright": {"type": "npm", "package": "playwright", "description": "Browser testing"},

    # Utilities
    "lodash": {"type": "npm", "package": "lodash", "description": "Utility library"},
    "howler": {"type": "npm", "package": "howler", "description": "Audio library"},
    "gsap": {"type": "npm", "package": "gsap", "description": "Animation library"},
    "matter-js": {"type": "npm", "package": "matter-js", "description": "2D physics engine"},
    "planck": {"type": "npm", "package": "planck", "description": "2D physics (Box2D)"},

    # Python game dev
    "pygame": {"type": "pip", "package": "pygame", "description": "Python game library"},
    "pyglet": {"type": "pip", "package": "pyglet", "description": "Python multimedia"},
    "arcade": {"type": "pip", "package": "arcade", "description": "Python game library"},
    "panda3d": {"type": "pip", "package": "panda3d", "description": "3D game engine"},

    # Asset tools
    "sharp": {"type": "npm", "package": "sharp", "description": "Image processing"},
    "imagemin": {"type": "npm", "package": "imagemin", "description": "Image optimization"},
    "ffmpeg": {"type": "system", "package": "ffmpeg", "description": "Media processing"},
}

# Game project templates
PROJECT_TEMPLATES = {
    "web-game": {
        "description": "HTML5/JavaScript browser game",
        "structure": {
            "src/": {
                "index.ts": "// Main entry point\nimport { Game } from './game';\n\nconst game = new Game();\ngame.start();",
                "game.ts": "// Game class\nexport class Game {\n  constructor() {}\n  start() { console.log('Game started!'); }\n}",
                "scenes/": {
                    "MainScene.ts": "// Main game scene",
                    "MenuScene.ts": "// Menu scene",
                    "GameOverScene.ts": "// Game over scene",
                },
                "entities/": {
                    "Player.ts": "// Player entity",
                    "Enemy.ts": "// Enemy base class",
                    "Tower.ts": "// Tower base class (for TD games)",
                },
                "systems/": {
                    "InputSystem.ts": "// Input handling",
                    "PhysicsSystem.ts": "// Physics/collision",
                    "RenderSystem.ts": "// Rendering",
                    "ProgressionSystem.ts": "// Prestige/progression",
                },
                "ui/": {
                    "HUD.ts": "// Heads-up display",
                    "Menu.ts": "// Menu components",
                    "PrestigeUI.ts": "// Prestige/upgrade UI",
                },
                "data/": {
                    "config.json": '{\n  "gameName": "Untitled Game",\n  "version": "0.1.0"\n}',
                    "towers.json": "[]",
                    "upgrades.json": "[]",
                    "prestige.json": "[]",
                },
                "utils/": {
                    "math.ts": "// Math utilities",
                    "storage.ts": "// Save/load system",
                },
            },
            "public/": {
                "index.html": '<!DOCTYPE html>\n<html>\n<head>\n  <title>Game</title>\n  <style>* { margin: 0; padding: 0; } canvas { display: block; }</style>\n</head>\n<body>\n  <script type="module" src="/src/index.ts"></script>\n</body>\n</html>',
                "assets/": {
                    "images/": {},
                    "audio/": {},
                    "fonts/": {},
                    "data/": {},
                },
            },
            "docs/": {
                "GDD.md": "# Game Design Document\n\n## Overview\n\n## Mechanics\n\n## Progression\n\n## Art Style\n",
                "TECHNICAL.md": "# Technical Documentation\n\n## Architecture\n\n## Systems\n",
                "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n",
            },
            "tests/": {
                "game.test.ts": "// Game tests",
            },
            ".gitignore": "node_modules/\ndist/\n.env\n*.log\n.DS_Store",
            "package.json": None,  # Generated dynamically
            "tsconfig.json": '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "module": "ESNext",\n    "moduleResolution": "bundler",\n    "strict": true,\n    "esModuleInterop": true,\n    "skipLibCheck": true,\n    "outDir": "dist"\n  },\n  "include": ["src"]\n}',
            "vite.config.ts": 'import { defineConfig } from "vite";\n\nexport default defineConfig({\n  base: "./",\n  build: { outDir: "dist" }\n});',
            "README.md": None,  # Generated dynamically
        },
        "dependencies": ["vite", "typescript"],
    },
    "incremental-game": {
        "description": "Incremental/idle game with prestige system",
        "structure": {
            "src/": {
                "index.ts": "// Incremental Game Entry",
                "core/": {
                    "GameState.ts": "// Central game state manager",
                    "SaveSystem.ts": "// Auto-save and load",
                    "TickSystem.ts": "// Game loop and offline progress",
                },
                "systems/": {
                    "ResourceSystem.ts": "// Resource generation and management",
                    "UpgradeSystem.ts": "// Upgrade purchasing and effects",
                    "PrestigeSystem.ts": "// Prestige layers and bonuses",
                    "AchievementSystem.ts": "// Achievements and milestones",
                    "ChallengeSystem.ts": "// Challenge modes",
                },
                "data/": {
                    "resources.json": "[]",
                    "upgrades.json": "[]",
                    "prestige-tiers.json": "[]",
                    "achievements.json": "[]",
                    "challenges.json": "[]",
                },
                "ui/": {
                    "ResourceDisplay.ts": "",
                    "UpgradePanel.ts": "",
                    "PrestigePanel.ts": "",
                    "StatsPanel.ts": "",
                    "SettingsPanel.ts": "",
                },
            },
            "public/": {
                "index.html": "",
                "assets/": {"images/": {}, "audio/": {}},
            },
            "docs/": {
                "GDD.md": "# Incremental Game Design Document",
                "BALANCE.md": "# Balance Documentation",
                "FORMULAS.md": "# Mathematical Formulas",
            },
        },
        "dependencies": ["vite", "typescript", "lodash"],
    },
    "tower-defense": {
        "description": "Tower defense game template",
        "structure": {
            "src/": {
                "index.ts": "// Tower Defense Entry",
                "core/": {
                    "Game.ts": "",
                    "Map.ts": "// Map/level system",
                    "WaveManager.ts": "// Enemy wave spawning",
                    "PathFinder.ts": "// Enemy pathing",
                },
                "entities/": {
                    "towers/": {
                        "BaseTower.ts": "",
                        "ArrowTower.ts": "",
                        "CannonTower.ts": "",
                        "MagicTower.ts": "",
                        "SlowTower.ts": "",
                    },
                    "enemies/": {
                        "BaseEnemy.ts": "",
                        "FastEnemy.ts": "",
                        "TankEnemy.ts": "",
                        "FlyingEnemy.ts": "",
                        "BossEnemy.ts": "",
                    },
                    "projectiles/": {
                        "BaseProjectile.ts": "",
                        "Arrow.ts": "",
                        "Cannonball.ts": "",
                        "MagicBolt.ts": "",
                    },
                },
                "systems/": {
                    "TowerPlacement.ts": "",
                    "CombatSystem.ts": "",
                    "UpgradeSystem.ts": "",
                    "EconomySystem.ts": "",
                    "PrestigeSystem.ts": "",
                },
                "data/": {
                    "towers.json": "[]",
                    "enemies.json": "[]",
                    "waves.json": "[]",
                    "maps.json": "[]",
                    "upgrades.json": "[]",
                    "prestige.json": "[]",
                },
                "ui/": {
                    "TowerSelector.ts": "",
                    "WaveInfo.ts": "",
                    "UpgradeMenu.ts": "",
                    "PrestigeScreen.ts": "",
                },
            },
            "public/": {
                "index.html": "",
                "assets/": {
                    "images/": {
                        "towers/": {},
                        "enemies/": {},
                        "projectiles/": {},
                        "maps/": {},
                        "ui/": {},
                    },
                    "audio/": {
                        "sfx/": {},
                        "music/": {},
                    },
                },
            },
            "docs/": {
                "GDD.md": "# Tower Defense Game Design Document",
                "TOWERS.md": "# Tower Documentation",
                "ENEMIES.md": "# Enemy Documentation",
                "WAVES.md": "# Wave Balance Documentation",
                "PRESTIGE.md": "# Prestige System Documentation",
            },
        },
        "dependencies": ["vite", "typescript", "phaser"],
    },
}


class ProjectBuilder:
    """High-level project management for game development."""

    def __init__(self, project_name: str, base_path: Optional[Path] = None):
        self.project_name = self._sanitize_name(project_name)
        self.base_path = base_path or PROJECTS_BASE
        self.project_path = self.base_path / self.project_name
        self.installed_tools: List[str] = []
        self.log_entries: List[str] = []

    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for filesystem."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in name.lower())

    def _log(self, message: str):
        """Log an action."""
        entry = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        self.log_entries.append(entry)
        logger.info(message)

    async def create_directory(self, path: Union[str, Path], exist_ok: bool = True) -> Dict[str, Any]:
        """Create a directory."""
        full_path = self.project_path / path if not Path(path).is_absolute() else Path(path)
        try:
            full_path.mkdir(parents=True, exist_ok=exist_ok)
            self._log(f"Created directory: {full_path}")
            return {"success": True, "path": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def create_file(self, path: Union[str, Path], content: str = "") -> Dict[str, Any]:
        """Create a file with content."""
        full_path = self.project_path / path if not Path(path).is_absolute() else Path(path)
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            self._log(f"Created file: {full_path}")
            return {"success": True, "path": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def append_file(self, path: Union[str, Path], content: str) -> Dict[str, Any]:
        """Append content to a file."""
        full_path = self.project_path / path if not Path(path).is_absolute() else Path(path)
        try:
            async with aiofiles.open(full_path, 'a', encoding='utf-8') as f:
                await f.write(content)
            self._log(f"Appended to file: {full_path}")
            return {"success": True, "path": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def read_file(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Read a file's content."""
        full_path = self.project_path / path if not Path(path).is_absolute() else Path(path)
        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return {"success": True, "content": content, "path": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_directory(self, path: Union[str, Path] = ".") -> Dict[str, Any]:
        """List directory contents."""
        full_path = self.project_path / path if path != "." else self.project_path
        try:
            items = []
            for item in full_path.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            return {"success": True, "path": str(full_path), "items": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_path(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Delete a file or directory."""
        full_path = self.project_path / path if not Path(path).is_absolute() else Path(path)

        # Safety check - don't delete outside project
        if not str(full_path).startswith(str(self.project_path)):
            return {"success": False, "error": "Cannot delete outside project directory"}

        try:
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()
            self._log(f"Deleted: {full_path}")
            return {"success": True, "deleted": str(full_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def copy_path(self, src: Union[str, Path], dst: Union[str, Path]) -> Dict[str, Any]:
        """Copy a file or directory."""
        src_path = self.project_path / src if not Path(src).is_absolute() else Path(src)
        dst_path = self.project_path / dst if not Path(dst).is_absolute() else Path(dst)
        try:
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            self._log(f"Copied: {src_path} -> {dst_path}")
            return {"success": True, "source": str(src_path), "destination": str(dst_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def move_path(self, src: Union[str, Path], dst: Union[str, Path]) -> Dict[str, Any]:
        """Move a file or directory."""
        src_path = self.project_path / src if not Path(src).is_absolute() else Path(src)
        dst_path = self.project_path / dst if not Path(dst).is_absolute() else Path(dst)
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            self._log(f"Moved: {src_path} -> {dst_path}")
            return {"success": True, "source": str(src_path), "destination": str(dst_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class PackageManager:
    """Manages package installation for projects."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.installed_packages: List[str] = []

    async def check_manager_available(self, manager: str) -> bool:
        """Check if a package manager is available."""
        if manager not in PACKAGE_MANAGERS:
            return False

        check_cmd = PACKAGE_MANAGERS[manager]["check"]
        try:
            result = subprocess.run(
                check_cmd,
                shell=True,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    async def init_project(self, manager: str = "npm") -> Dict[str, Any]:
        """Initialize a project with a package manager."""
        if manager not in PACKAGE_MANAGERS:
            return {"success": False, "error": f"Unknown package manager: {manager}"}

        init_cmd = PACKAGE_MANAGERS[manager].get("init")
        if not init_cmd:
            return {"success": True, "message": f"{manager} does not require initialization"}

        try:
            result = subprocess.run(
                init_cmd,
                cwd=str(self.project_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_package(self, package: str, manager: str = "npm", dev: bool = False) -> Dict[str, Any]:
        """Install a package."""
        if manager not in PACKAGE_MANAGERS:
            return {"success": False, "error": f"Unknown package manager: {manager}"}

        install_cmd = PACKAGE_MANAGERS[manager]["install"]
        if manager == "npm" and dev:
            install_cmd += " --save-dev"
        elif manager == "yarn" and dev:
            install_cmd += " --dev"
        elif manager == "pip" and dev:
            pass  # pip doesn't have dev dependencies concept

        full_cmd = f"{install_cmd} {package}"

        try:
            logger.info(f"Installing package: {full_cmd}")
            result = subprocess.run(
                full_cmd,
                cwd=str(self.project_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for large packages
            )

            if result.returncode == 0:
                self.installed_packages.append(package)

            return {
                "success": result.returncode == 0,
                "package": package,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Installation timed out for {package}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_approved_tool(self, tool_name: str) -> Dict[str, Any]:
        """Install an approved tool from the whitelist."""
        if tool_name not in APPROVED_TOOLS:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not in the approved list. Available: {list(APPROVED_TOOLS.keys())}"
            }

        tool_info = APPROVED_TOOLS[tool_name]

        if tool_info["type"] == "system":
            return {
                "success": False,
                "error": f"Tool '{tool_name}' requires system installation. Please install manually.",
                "description": tool_info["description"]
            }

        return await self.install_package(
            tool_info["package"],
            manager=tool_info["type"]
        )


class ToolExecutor:
    """Executes external tools and commands."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.command_history: List[Dict[str, Any]] = []

    async def run_command(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout: int = 120,
        capture_output: bool = True
    ) -> Dict[str, Any]:
        """Run a shell command."""
        work_dir = cwd or self.project_path

        # Security check - basic sanitization
        dangerous_patterns = ['rm -rf /', 'mkfs', 'dd if=/dev/', ':(){', 'chmod -R 777 /']
        for pattern in dangerous_patterns:
            if pattern in command.lower():
                return {"success": False, "error": f"Blocked dangerous command pattern"}

        try:
            logger.info(f"Executing: {command} in {work_dir}")

            result = subprocess.run(
                command,
                cwd=str(work_dir),
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )

            self.command_history.append({
                "command": command,
                "cwd": str(work_dir),
                "returncode": result.returncode,
                "timestamp": datetime.now().isoformat()
            })

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout if capture_output else None,
                "stderr": result.stderr if capture_output else None,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out ({timeout}s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_build(self, build_command: str = "npm run build") -> Dict[str, Any]:
        """Run the project build."""
        return await self.run_command(build_command, timeout=300)

    async def run_dev_server(self, command: str = "npm run dev") -> Dict[str, Any]:
        """Start the development server (runs in background)."""
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.project_path),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return {
                "success": True,
                "pid": process.pid,
                "message": f"Dev server started with PID {process.pid}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


async def scaffold_project(
    project_name: str,
    template: str = "web-game",
    base_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Scaffold a new game project from a template.

    Args:
        project_name: Name of the project
        template: Template to use (web-game, incremental-game, tower-defense)
        base_path: Base path for projects
    """
    if template not in PROJECT_TEMPLATES:
        return {
            "success": False,
            "error": f"Unknown template: {template}. Available: {list(PROJECT_TEMPLATES.keys())}"
        }

    builder = ProjectBuilder(project_name, base_path)
    template_data = PROJECT_TEMPLATES[template]

    # Create project directory
    await builder.create_directory(".")

    # Create structure recursively
    async def create_structure(structure: Dict, path: str = ""):
        for name, content in structure.items():
            current_path = f"{path}/{name}" if path else name

            if isinstance(content, dict):
                # It's a directory
                await builder.create_directory(current_path)
                await create_structure(content, current_path)
            elif content is None:
                # Generate dynamic content
                if name == "package.json":
                    pkg_content = json.dumps({
                        "name": project_name,
                        "version": "0.1.0",
                        "type": "module",
                        "scripts": {
                            "dev": "vite",
                            "build": "vite build",
                            "preview": "vite preview"
                        }
                    }, indent=2)
                    await builder.create_file(current_path, pkg_content)
                elif name == "README.md":
                    readme = f"# {project_name}\n\n{template_data['description']}\n\n## Getting Started\n\n```bash\nnpm install\nnpm run dev\n```\n"
                    await builder.create_file(current_path, readme)
            else:
                # It's a file with content
                await builder.create_file(current_path, content)

    await create_structure(template_data["structure"])

    # Initialize package manager and install dependencies
    pkg_manager = PackageManager(builder.project_path)

    # Check if npm is available
    if await pkg_manager.check_manager_available("npm"):
        # Install template dependencies
        for dep in template_data.get("dependencies", []):
            if dep in APPROVED_TOOLS:
                await pkg_manager.install_approved_tool(dep)

    return {
        "success": True,
        "project_path": str(builder.project_path),
        "template": template,
        "log": builder.log_entries
    }


# Export all tools for use in agent nodes
__all__ = [
    'ProjectBuilder',
    'PackageManager',
    'ToolExecutor',
    'scaffold_project',
    'APPROVED_TOOLS',
    'PROJECT_TEMPLATES',
    'PROJECTS_BASE',
]
