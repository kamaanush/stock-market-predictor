import { api } from "./api";
import { ScannerResult } from "../types/scanner";

export async function scanStock(
    symbol: string,
    interval="5m"
){
    return api<ScannerResult>(
        `/scanner/${symbol}?interval=${interval}`
    );
}

export async function getWatchlist(){
    return api<any[]>("/watchlist");
}