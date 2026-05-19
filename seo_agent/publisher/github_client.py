"""GitHub REST API v3 client — creates branch, commits files, opens PR. Never pushes to main."""
from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

API = "https://api.github.com"


@dataclass
class FileToCommit:
    path: str  # e.g. "blog/how-to-pass-texas-exam.html"
    content: str  # file content (will be base64-encoded)


@dataclass
class PublishResult:
    branch: str
    pr_url: str | None = None
    files_committed: list[str] = field(default_factory=list)
    dry_run: bool = False


class GitHubPublisher:
    """Publish generated content to a GitHub repo via Pull Request."""

    def __init__(self, token: str, owner: str, repo: str, base_branch: str = "main"):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_branch = base_branch
        self._session = None

    @property
    def session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        return self._session

    def _url(self, path: str) -> str:
        return f"{API}/repos/{self.owner}/{self.repo}{path}"

    def _get_base_sha(self) -> str:
        """Get the SHA of the base branch HEAD."""
        resp = self.session.get(self._url(f"/git/ref/heads/{self.base_branch}"))
        resp.raise_for_status()
        return resp.json()["object"]["sha"]

    def _create_branch(self, branch_name: str, sha: str) -> None:
        """Create a new branch from the given SHA."""
        resp = self.session.post(self._url("/git/refs"), json={
            "ref": f"refs/heads/{branch_name}",
            "sha": sha,
        })
        resp.raise_for_status()
        logger.info(f"Created branch: {branch_name}")

    def _commit_file(self, branch: str, file: FileToCommit, message: str) -> None:
        """Create or update a file on the branch."""
        import base64
        encoded = base64.b64encode(file.content.encode()).decode()

        # Check if file exists (to get its SHA for update)
        existing_sha = None
        resp = self.session.get(self._url(f"/contents/{file.path}"), params={"ref": branch})
        if resp.status_code == 200:
            existing_sha = resp.json()["sha"]

        payload: dict[str, Any] = {
            "message": message,
            "content": encoded,
            "branch": branch,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        resp = self.session.put(self._url(f"/contents/{file.path}"), json=payload)
        resp.raise_for_status()

    def _create_pr(self, branch: str, title: str, body: str) -> str:
        """Create a Pull Request and return its URL."""
        resp = self.session.post(self._url("/pulls"), json={
            "title": title,
            "body": body,
            "head": branch,
            "base": self.base_branch,
        })
        resp.raise_for_status()
        pr_url = resp.json()["html_url"]
        logger.info(f"Created PR: {pr_url}")
        return pr_url

    def publish(self, files: list[FileToCommit], title: str, body: str = "",
                dry_run: bool = False) -> PublishResult:
        """Publish files via a new branch + PR. Never touches main directly."""
        timestamp = int(time.time())
        slug = title.lower().replace(" ", "-")[:30].rstrip("-")
        branch_name = f"seo/{slug}-{timestamp}"

        if dry_run:
            logger.info(f"[DRY RUN] Would create branch '{branch_name}' with {len(files)} files")
            return PublishResult(
                branch=branch_name,
                files_committed=[f.path for f in files],
                dry_run=True,
            )

        # Real publish
        base_sha = self._get_base_sha()
        self._create_branch(branch_name, base_sha)

        for f in files:
            commit_msg = f"seo: add {f.path}"
            self._commit_file(branch_name, f, commit_msg)
            logger.info(f"Committed: {f.path}")

        pr_url = self._create_pr(branch_name, title, body)

        return PublishResult(
            branch=branch_name,
            pr_url=pr_url,
            files_committed=[f.path for f in files],
        )
