from app.config import get_settings
from app.providers.base import CachedHTTPClient, ProviderError
from app.schemas.market import Filing


class SECEdgarProvider:
    name = "SEC EDGAR"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = CachedHTTPClient("sec_edgar")

    async def company_filings(self, symbol: str, limit: int = 10) -> list[Filing]:
        tickers = await self.client.get_json(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": self.settings.sec_user_agent},
            ttl_seconds=86400,
        )
        match = next((row for row in tickers.values() if row.get("ticker", "").upper() == symbol.upper()), None)
        if not match:
            return []

        cik = str(match["cik_str"]).zfill(10)
        data = await self.client.get_json(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers={"User-Agent": self.settings.sec_user_agent},
            ttl_seconds=3600,
        )
        recent = data.get("filings", {}).get("recent", {})
        filings: list[Filing] = []
        for form, filing_date, accession in zip(
            recent.get("form", []),
            recent.get("filingDate", []),
            recent.get("accessionNumber", []),
            strict=False,
        ):
            if len(filings) >= limit:
                break
            accession_clean = accession.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{accession}-index.html"
            filings.append(Filing(filing_type=form, filing_date=filing_date, accession_number=accession, url=url))
        return filings
