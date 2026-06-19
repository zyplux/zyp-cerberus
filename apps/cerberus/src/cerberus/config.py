from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class Config:
    org: str
    exclude_repos: tuple[str, ...]
    ruleset_name: str
    default_recipe_marker: str
    required_aliases: dict[str, str]
    recommended_aliases: dict[str, str]
    required_recipes: tuple[str, ...]
    recommended_recipes: tuple[str, ...]
    check_pipeline: tuple[str, ...]
    wrapped_tools: tuple[str, ...]
    allowed_setup_actions: tuple[str, ...]


def _from_dict(data: dict) -> Config:
    aliases = data.get("aliases", {})
    recipes = data.get("recipes", {})
    ci = data.get("ci", {})
    return Config(
        org=data["org"],
        exclude_repos=tuple(data.get("exclude_repos", [])),
        ruleset_name=data["ruleset_name"],
        default_recipe_marker=data["default_recipe_marker"],
        required_aliases=dict(aliases.get("required", {})),
        recommended_aliases=dict(aliases.get("recommended", {})),
        required_recipes=tuple(recipes.get("required", [])),
        recommended_recipes=tuple(recipes.get("recommended", [])),
        check_pipeline=tuple(recipes.get("check_pipeline", [])),
        wrapped_tools=tuple(recipes.get("wrapped_tools", [])),
        allowed_setup_actions=tuple(ci.get("allowed_setup_actions", [])),
    )


def load(path: Path | None = None) -> Config:
    if path is not None:
        return _from_dict(tomllib.loads(path.read_text()))
    bundled = resources.files("cerberus").joinpath("cerberus.toml").read_text()
    return _from_dict(tomllib.loads(bundled))
