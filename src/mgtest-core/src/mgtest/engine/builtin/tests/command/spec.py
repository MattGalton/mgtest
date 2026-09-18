from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from mgtest.api.test import TestSpec
from mgtest.engine.builtin.tests.command.instance import CommandInstance


class Command(TestSpec):
    """Run a shell or Python command and assert its exit status and output."""

    shell_command: str | None = Field(default=None, description="Shell command to run; specify this or python_command.")
    python_command: str | None = Field(default=None, description="Python code to run; specify this or shell_command.")
    cwd: Path | None = Field(default=None, description="Working directory for the command.")
    environment: dict[str, str] = Field(default_factory=dict, description="Environment variables added to the command process.")
    timeout: float = Field(default=30.0, gt=0, description="Maximum command runtime in seconds.")
    expected_exit_code: int = Field(default=0, description="Exit status required for the check to pass.")
    stdout_contains: str | None = Field(default=None, description="Text that must occur in standard output.")
    stderr_contains: str | None = Field(default=None, description="Text that must occur in standard error.")

    @model_validator(mode="after")
    def require_one_command(self):
        if (self.shell_command is None) == (self.python_command is None):
            raise ValueError("Specify exactly one of 'shell_command' or 'python_command'")
        return self

    class Output(BaseModel):
        exit_code: int = Field(default=0, description="Exit status returned by the command.")
        stdout: str = Field(default="", description="Captured standard output.")
        stderr: str = Field(default="", description="Captured standard error.")

    def create_instance(self) -> CommandInstance:
        return CommandInstance(self)
