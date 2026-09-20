"""Accounts service -- Tag Manager account listing, reading and settings.

Covers the ``accounts`` resource in full: list, get, update.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import account_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import Account, ListAccountsResponse

logger = get_logger(__name__)


class AccountsService:
    """Read and update the Tag Manager accounts a user can see."""

    def list_accounts(
        self,
        ctx: Context,
        page_token: Optional[str] = None,
        include_google_tags: Optional[bool] = None,
    ) -> Awaitable[ListAccountsResponse]:
        """List every account the authenticated user has access to.

        Args:
            ctx: FastMCP context.
            page_token: Continuation token from a previous response.
            include_google_tags: Also return accounts that exist only as Google
                tag (gtag.js) destinations rather than as Tag Manager accounts.
        """
        client = get_client()
        return execute(
            ctx,
            "listing accounts",
            lambda: (
                client.service.accounts()
                .list(
                    **optional(
                        pageToken=page_token, includeGoogleTags=include_google_tags
                    )
                )
                .execute()
            ),
        )

    def get_account(self, ctx: Context, account_id: str) -> Awaitable[Account]:
        """Retrieve one account.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
        """
        client = get_client()
        path = account_path(account_id)
        return execute(
            ctx,
            f"getting account {path}",
            lambda: client.service.accounts().get(path=path).execute(),
        )

    async def update_account(
        self,
        ctx: Context,
        account_id: str,
        account: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Account:
        """Update an account's settings.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            account: Account resource carrying the fields to change, e.g.
                ``{"name": "New name", "shareData": true}``.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the account.
        """
        client = get_client()
        client.require_write("update_account")
        path = account_path(account_id)
        result = await execute(
            ctx,
            f"updating account {path}",
            lambda: (
                client.service.accounts()
                .update(
                    path=path,
                    body=cast("Account", account),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Updated account %s", path)
        return result


def create_accounts_tools(
    service: AccountsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by an AccountsService instance."""
    # FastMCP resolves tool annotations at runtime. The tagmanager stub types
    # exist only at type-check time, so tool signatures below use Dict[str, Any]
    # while the service layer above stays precisely typed against the stubs.

    async def list_accounts(
        ctx: Context,
        page_token: Optional[str] = None,
        include_google_tags: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List the Google Tag Manager accounts this user can access.

        Start here: every other tool needs an account ID, and the numbers shown
        in the Tag Manager web UI's URL are not always the API's account IDs.

        Args:
            page_token: Continuation token from a previous response.
            include_google_tags: Also return accounts that exist only as Google
                tag destinations.

        Returns:
            Each account's path, accountId, name and shareData flag, plus
            nextPageToken when more results exist.
        """
        return cast(
            Dict[str, Any],
            await service.list_accounts(ctx, page_token, include_google_tags),
        )

    async def get_account(ctx: Context, account_id: str) -> Dict[str, Any]:
        """Get one Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.

        Returns:
            The account's path, accountId, name, shareData flag and fingerprint.
        """
        return cast(Dict[str, Any], await service.get_account(ctx, account_id))

    async def update_account(
        ctx: Context,
        account_id: str,
        account: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a Tag Manager account's settings.

        Args:
            account_id: Numeric Tag Manager account ID.
            account: Account resource with the fields to change, e.g.
                {"name": "Acme Inc", "shareData": false}.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the account changed in the meantime.

        Returns:
            The updated account.
        """
        return cast(
            Dict[str, Any],
            await service.update_account(ctx, account_id, account, fingerprint),
        )

    return [list_accounts, get_account, update_account]


def register_accounts_tools(mcp: FastMCP[Any]) -> AccountsService:
    """Register the accounts tools with an MCP server.

    Returns the service instance so tests can reach it.
    """
    service = AccountsService()
    for tool in create_accounts_tools(service):
        mcp.tool(tool)
    return service
