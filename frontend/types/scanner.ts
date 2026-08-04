export interface ScannerSignal {
  id: string;
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  entryPrice?: number;
  targetPrice?: number;
  stopLoss?: number;
  rationale?: string;
  timestamp?: string;
}

export interface ScannerResponse {
  signals: ScannerSignal[];
  generatedAt?: string;
}
¯export interface ScannerResult {

    symbol: string;

    signal: string;

    score: number;

    grade: string;

    trend: string;

    reason: string;

    entry_price?: number;

    stoploss?: number;

    target1?: number;

    target2?: number;

    action_status: string;

}