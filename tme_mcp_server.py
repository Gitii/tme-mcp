import logging
from urllib.parse import quote

from mcp_app import mcp
from tme_auth import _make_request, TME_COUNTRY, TME_CURRENCY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

logger.info("=== STARTING TME MCP SERVER ===")

# Tools are registered at import time via @mcp.tool() decorators below.

# ---------------------------------------------------------------------------
# Search & Browse
# ---------------------------------------------------------------------------


@mcp.tool()
def search_products(
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
    category_id: int | None = None,
    manufacturer_id: int | None = None,
    with_stock: bool = False,
    sort: str | None = None,
) -> dict:
    """Search TME products by keyword, part number, or category.

    Provide `search`, `category_id`, or both. Returns products plus result counters.

    Args:
        search: Search phrase or part number (2-40 characters)
        page: Page number (default: 1)
        limit: Results per page, 1-100 (default: 20)
        category_id: Optional category ID filter
        manufacturer_id: Optional manufacturer ID filter
        with_stock: Only return products that are in stock (default: False)
        sort: Sort order: SYMBOL, ACCURACY, ORIGINAL_SYMBOL, PRICE_FIRST_QUANTITY,
            PRICE_LAST_QUANTITY, ACCURACY_IN_STOCK_FIRST, AVAILABLE_IN_STOCK_FIRST
    """
    params = {
        "phrase": search,
        "category_id": category_id,
        "manufacturer_id": manufacturer_id,
        "page": page,
        "limit": limit,
        "scope": ["products", "counters"],
    }
    if with_stock:
        params["filter[in_stock]"] = True
    if sort:
        params["sort[property]"] = sort
    return _make_request("products/search", params)


@mcp.tool()
def get_categories(category_id: int | None = None, tree: bool = True) -> dict:
    """Get TME product categories.

    Args:
        category_id: Root category ID to start from. Omit for the full catalog.
        tree: Return nested tree (True) or a flat list (False)
    """
    endpoint = "products/categories/tree" if tree else "products/categories/list"
    return _make_request(endpoint, {"root_category_id": category_id})


@mcp.tool()
def search_parameters(category_id: int, search: str | None = None) -> dict:
    """Get available filter parameters (and their values) for a category.

    Args:
        category_id: Category ID to get filter parameters for
        search: Optional search phrase to narrow the parameter set
    """
    params = {"category_id": category_id, "phrase": search, "scope": ["parameters"], "limit": 1}
    return _make_request("products/search", params)


@mcp.tool()
def get_manufacturers(category_id: int | None = None) -> dict:
    """List manufacturers, optionally restricted to a category.

    Args:
        category_id: Optional category ID filter
    """
    return _make_request("products/manufacturers", {"category_id": category_id})


# ---------------------------------------------------------------------------
# Product Details
# ---------------------------------------------------------------------------


@mcp.tool()
def get_products(symbols: list[str] | None = None, mpns: list[str] | None = None) -> dict:
    """Get full product details for up to 50 TME symbols or manufacturer part numbers.

    Provide either `symbols` or `mpns`.

    Args:
        symbols: List of TME product symbols (max 50)
        mpns: List of manufacturer part numbers (max 50)
    """
    params = {}
    if symbols:
        params["symbols"] = symbols[:50]
    elif mpns:
        params["mpns"] = mpns[:50]
    return _make_request("products", params)


@mcp.tool()
def get_parameters(symbols: list[str]) -> dict:
    """Get technical specifications/attributes for up to 50 products.

    Args:
        symbols: List of TME product symbols (max 50)
    """
    return _make_request("products/parameters", {"symbols": symbols[:50]})


@mcp.tool()
def get_product_files(symbols: list[str]) -> dict:
    """Get datasheets, photos, and other files for up to 50 products.

    Args:
        symbols: List of TME product symbols (max 50)
    """
    return _make_request("products/files", {"symbols": symbols[:50]})


@mcp.tool()
def get_similar_products(symbol: str) -> dict:
    """Get similar/alternative products for a given part.

    Args:
        symbol: TME product symbol
    """
    return _make_request("products/similar", {"symbol": symbol})


@mcp.tool()
def get_related_products(symbol: str) -> dict:
    """Get related products (accessories, complementary items) for a given part.

    Args:
        symbol: TME product symbol
    """
    return _make_request("products/related", {"symbol": symbol})


# ---------------------------------------------------------------------------
# Pricing & Stock
# ---------------------------------------------------------------------------


def _product_data(symbols: list[str], scope: list[str], amounts: list[int] | None = None) -> dict:
    symbols = symbols[:50]
    params = {"symbols": symbols, "scope": scope, "currency": TME_CURRENCY}
    if amounts is not None:
        amounts = (amounts + [1] * len(symbols))[: len(symbols)]
        params["amounts"] = amounts
    return _make_request("products/data", params)


@mcp.tool()
def get_prices(symbols: list[str]) -> dict:
    """Get pricing with volume tiers for up to 50 products.

    Prices returned in the configured currency (default: {currency}).

    Args:
        symbols: List of TME product symbols (max 50)
    """.format(currency=TME_CURRENCY)
    return _product_data(symbols, ["prices"])


@mcp.tool()
def get_stocks(symbols: list[str]) -> dict:
    """Get stock/inventory levels for up to 50 products.

    Args:
        symbols: List of TME product symbols (max 50)
    """
    return _product_data(symbols, ["stock"])


@mcp.tool()
def get_prices_and_stocks(symbols: list[str]) -> dict:
    """Get combined pricing and stock for up to 50 products.

    Prices returned in the configured currency (default: {currency}).

    Args:
        symbols: List of TME product symbols (max 50)
    """.format(currency=TME_CURRENCY)
    return _product_data(symbols, ["prices", "stock"])


# ---------------------------------------------------------------------------
# Other
# ---------------------------------------------------------------------------


@mcp.tool()
def get_delivery_time(symbols: list[str], amounts: list[int] | None = None) -> dict:
    """Get estimated delivery time for up to 50 products.

    Args:
        symbols: List of TME product symbols (max 50)
        amounts: Quantity per symbol, same order as symbols (defaults to 1 each)
    """
    return _product_data(symbols, ["delivery"], amounts or [])


@mcp.tool()
def generate_tme_url(symbol: str) -> str:
    """Generate a TME product page URL.

    Args:
        symbol: TME product symbol
    """
    country = TME_COUNTRY.lower()
    return f"https://www.tme.eu/{country}/en/details/{quote(symbol)}/"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


logger.info("=== SERVER READY ===")


def main():
    mcp.run()


if __name__ == "__main__":
    main()
