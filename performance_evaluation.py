#!/usr/bin/env python3
"""
Performance Evaluation and Backtesting Module for CryptoRocket
Implements comprehensive metrics and backtesting for the ML trading system
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

@dataclass
class TradeResult:
    """Represents a single trade result"""
    entry_time: datetime
    exit_time: datetime
    asset: str
    signal: str  # LONG, SHORT, NEUTRAL
    entry_price: float
    exit_price: float
    return_pct: float
    confidence: float
    hold_time: timedelta

class PerformanceMetrics:
    """Calculate comprehensive performance metrics"""
    
    @staticmethod
    def calculate_returns(prices: np.ndarray) -> np.ndarray:
        """Calculate returns from price series"""
        return np.diff(prices) / prices[:-1]
    
    @staticmethod
    def sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0.0
        return (np.mean(returns) - risk_free_rate / 252) / np.std(returns) * np.sqrt(252)
    
    @staticmethod
    def max_drawdown(returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return np.min(drawdown)
    
    @staticmethod
    def calmar_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Calmar ratio"""
        annual_return = np.mean(returns) * 252
        max_dd = abs(PerformanceMetrics.max_drawdown(returns))
        if max_dd == 0:
            return float('inf')
        return (annual_return - risk_free_rate) / max_dd
    
    @staticmethod
    def sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return float('inf')
        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return float('inf')
        return (np.mean(returns) - risk_free_rate / 252) / downside_deviation * np.sqrt(252)
    
    @staticmethod
    def win_rate(trades: List[TradeResult]) -> float:
        """Calculate win rate"""
        if not trades:
            return 0.0
        winning_trades = sum(1 for trade in trades if trade.return_pct > 0)
        return winning_trades / len(trades)
    
    @staticmethod
    def average_win_loss(trades: List[TradeResult]) -> Tuple[float, float]:
        """Calculate average win and average loss"""
        if not trades:
            return 0.0, 0.0
        
        wins = [trade.return_pct for trade in trades if trade.return_pct > 0]
        losses = [trade.return_pct for trade in trades if trade.return_pct < 0]
        
        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0
        
        return avg_win, avg_loss
    
    @staticmethod
    def profit_factor(trades: List[TradeResult]) -> float:
        """Calculate profit factor"""
        if not trades:
            return 0.0
        
        total_profit = sum(trade.return_pct for trade in trades if trade.return_pct > 0)
        total_loss = abs(sum(trade.return_pct for trade in trades if trade.return_pct < 0))
        
        if total_loss == 0:
            return float('inf') if total_profit > 0 else 0.0
        
        return total_profit / total_loss

class Backtester:
    """Backtesting engine for the ML trading system"""
    
    def __init__(self, initial_capital: float = 10000, transaction_cost: float = 0.001):
        """Initialize backtester"""
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.trades: List[TradeResult] = []
        self.portfolio_values: List[float] = []
        self.timestamps: List[datetime] = []
        
    def run_backtest(self, predictions: List[Dict], prices: List[float], 
                    timestamps: List[datetime], asset: str) -> Dict:
        """Run backtest on predictions"""
        capital = self.initial_capital
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0
        entry_time = None
        entry_confidence = 0
        
        for i, pred in enumerate(predictions):
            if i >= len(prices) - 1:  # Need next price for exit
                break
                
            current_price = prices[i]
            next_price = prices[i + 1]
            current_time = timestamps[i]
            
            signal = pred.get('signal', 'NEUTRAL')
            confidence = pred.get('confidence', 0.0)
            
            # Close existing position if signal changes or confidence drops
            if position != 0:
                should_close = (
                    signal == 'NEUTRAL' or 
                    (position == 1 and signal == 'SHORT') or
                    (position == -1 and signal == 'LONG') or
                    confidence < 0.5
                )
                
                if should_close:
                    # Close position
                    return_pct = (next_price / entry_price - 1) if position == 1 else (entry_price / next_price - 1)
                    return_pct -= self.transaction_cost * 2  # Entry and exit costs
                    
                    trade = TradeResult(
                        entry_time=entry_time,
                        exit_time=current_time,
                        asset=asset,
                        signal='LONG' if position == 1 else 'SHORT',
                        entry_price=entry_price,
                        exit_price=next_price,
                        return_pct=return_pct,
                        confidence=entry_confidence,
                        hold_time=current_time - entry_time
                    )
                    
                    self.trades.append(trade)
                    capital *= (1 + return_pct)
                    position = 0
            
            # Open new position if signal is strong enough
            if position == 0 and signal in ['LONG', 'SHORT'] and confidence > 0.6:
                position = 1 if signal == 'LONG' else -1
                entry_price = current_price
                entry_time = current_time
                entry_confidence = confidence
            
            # Record portfolio value
            self.portfolio_values.append(capital)
            self.timestamps.append(current_time)
        
        # Close any remaining position at the end
        if position != 0 and len(prices) > 0:
            final_price = prices[-1]
            return_pct = (final_price / entry_price - 1) if position == 1 else (entry_price / final_price - 1)
            return_pct -= self.transaction_cost  # Exit cost only
            
            trade = TradeResult(
                entry_time=entry_time,
                exit_time=timestamps[-1],
                asset=asset,
                signal='LONG' if position == 1 else 'SHORT',
                entry_price=entry_price,
                exit_price=final_price,
                return_pct=return_pct,
                confidence=entry_confidence,
                hold_time=timestamps[-1] - entry_time
            )
            
            self.trades.append(trade)
            capital *= (1 + return_pct)
        
        # Calculate performance metrics
        returns = self.calculate_portfolio_returns()
        
        return {
            'final_capital': capital,
            'total_return': (capital / self.initial_capital - 1) * 100,
            'total_trades': len(self.trades),
            'win_rate': PerformanceMetrics.win_rate(self.trades),
            'avg_win': PerformanceMetrics.average_win_loss(self.trades)[0],
            'avg_loss': PerformanceMetrics.average_win_loss(self.trades)[1],
            'profit_factor': PerformanceMetrics.profit_factor(self.trades),
            'sharpe_ratio': PerformanceMetrics.sharpe_ratio(returns),
            'max_drawdown': PerformanceMetrics.max_drawdown(returns) * 100,
            'calmar_ratio': PerformanceMetrics.calmar_ratio(returns),
            'sortino_ratio': PerformanceMetrics.sortino_ratio(returns)
        }
    
    def calculate_portfolio_returns(self) -> np.ndarray:
        """Calculate portfolio returns"""
        if len(self.portfolio_values) < 2:
            return np.array([])
        
        values = np.array(self.portfolio_values)
        return np.diff(values) / values[:-1]

class ModelEvaluator:
    """Comprehensive model evaluation"""
    
    def __init__(self):
        """Initialize evaluator"""
        self.metrics = PerformanceMetrics()
        self.backtester = Backtester()
    
    def evaluate_model_performance(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                 y_proba: np.ndarray) -> Dict:
        """Evaluate model performance metrics"""
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score, f1_score,
            roc_auc_score, confusion_matrix, classification_report
        )
        
        # Basic metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        
        # ROC AUC (if binary classification)
        roc_auc = 0.0
        if len(np.unique(y_true)) == 2:
            try:
                roc_auc = roc_auc_score(y_true, y_proba)
            except:
                roc_auc = 0.0
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': roc_auc,
            'confusion_matrix': cm.tolist()
        }
    
    def generate_performance_report(self, backtest_results: Dict, 
                                  model_metrics: Dict) -> str:
        """Generate comprehensive performance report"""
        report = f"""
# CryptoRocket Model Performance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Backtesting Results
- **Final Capital**: ${backtest_results['final_capital']:,.2f}
- **Total Return**: {backtest_results['total_return']:.2f}%
- **Total Trades**: {backtest_results['total_trades']}
- **Win Rate**: {backtest_results['win_rate']:.2%}
- **Average Win**: {backtest_results['avg_win']:.2%}
- **Average Loss**: {backtest_results['avg_loss']:.2%}
- **Profit Factor**: {backtest_results['profit_factor']:.2f}
- **Sharpe Ratio**: {backtest_results['sharpe_ratio']:.2f}
- **Max Drawdown**: {backtest_results['max_drawdown']:.2f}%
- **Calmar Ratio**: {backtest_results['calmar_ratio']:.2f}
- **Sortino Ratio**: {backtest_results['sortino_ratio']:.2f}

## Model Metrics
- **Accuracy**: {model_metrics['accuracy']:.3f}
- **Precision**: {model_metrics['precision']:.3f}
- **Recall**: {model_metrics['recall']:.3f}
- **F1 Score**: {model_metrics['f1_score']:.3f}
- **ROC AUC**: {model_metrics['roc_auc']:.3f}

## Performance Interpretation
"""
        
        # Add performance interpretation
        if backtest_results['total_return'] > 0:
            report += "✅ **Profitable Strategy**: The model shows positive returns.\n"
        else:
            report += "❌ **Unprofitable Strategy**: The model shows negative returns.\n"
        
        if backtest_results['sharpe_ratio'] > 1.0:
            report += "✅ **Good Risk-Adjusted Returns**: Sharpe ratio > 1.0\n"
        elif backtest_results['sharpe_ratio'] > 0.5:
            report += "⚠️ **Moderate Risk-Adjusted Returns**: Sharpe ratio between 0.5-1.0\n"
        else:
            report += "❌ **Poor Risk-Adjusted Returns**: Sharpe ratio < 0.5\n"
        
        if backtest_results['max_drawdown'] < 10:
            report += "✅ **Low Drawdown**: Max drawdown < 10%\n"
        elif backtest_results['max_drawdown'] < 20:
            report += "⚠️ **Moderate Drawdown**: Max drawdown 10-20%\n"
        else:
            report += "❌ **High Drawdown**: Max drawdown > 20%\n"
        
        if backtest_results['win_rate'] > 0.6:
            report += "✅ **High Win Rate**: Win rate > 60%\n"
        elif backtest_results['win_rate'] > 0.5:
            report += "⚠️ **Moderate Win Rate**: Win rate 50-60%\n"
        else:
            report += "❌ **Low Win Rate**: Win rate < 50%\n"
        
        return report
    
    def create_visualizations(self, backtest_results: Dict, trades: List[TradeResult]):
        """Create performance visualizations"""
        if not trades:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('CryptoRocket Performance Analysis', fontsize=16)
        
        # Portfolio value over time
        if self.backtester.portfolio_values:
            axes[0, 0].plot(self.backtester.timestamps, self.backtester.portfolio_values)
            axes[0, 0].set_title('Portfolio Value Over Time')
            axes[0, 0].set_xlabel('Date')
            axes[0, 0].set_ylabel('Portfolio Value ($)')
            axes[0, 0].grid(True)
        
        # Trade returns distribution
        returns = [trade.return_pct for trade in trades]
        axes[0, 1].hist(returns, bins=20, alpha=0.7, edgecolor='black')
        axes[0, 1].set_title('Trade Returns Distribution')
        axes[0, 1].set_xlabel('Return (%)')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].grid(True)
        
        # Win/Loss by signal type
        long_trades = [trade for trade in trades if trade.signal == 'LONG']
        short_trades = [trade for trade in trades if trade.signal == 'SHORT']
        
        if long_trades or short_trades:
            long_wins = sum(1 for trade in long_trades if trade.return_pct > 0)
            long_total = len(long_trades)
            short_wins = sum(1 for trade in short_trades if trade.return_pct > 0)
            short_total = len(short_trades)
            
            categories = ['LONG', 'SHORT']
            win_rates = [
                long_wins / long_total if long_total > 0 else 0,
                short_wins / short_total if short_total > 0 else 0
            ]
            
            axes[1, 0].bar(categories, win_rates, color=['green', 'red'], alpha=0.7)
            axes[1, 0].set_title('Win Rate by Signal Type')
            axes[1, 0].set_ylabel('Win Rate')
            axes[1, 0].set_ylim(0, 1)
            axes[1, 0].grid(True)
        
        # Cumulative returns
        if self.backtester.portfolio_values:
            returns = self.backtester.calculate_portfolio_returns()
            cumulative_returns = np.cumprod(1 + returns) - 1
            axes[1, 1].plot(cumulative_returns * 100)
            axes[1, 1].set_title('Cumulative Returns')
            axes[1, 1].set_xlabel('Time')
            axes[1, 1].set_ylabel('Cumulative Return (%)')
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.savefig('crypto_rocket_performance.png', dpi=300, bbox_inches='tight')
        plt.show()

def main():
    """Demonstrate performance evaluation"""
    print("📊 CryptoRocket Performance Evaluation")
    print("=" * 50)
    
    # Mock data for demonstration
    np.random.seed(42)
    n_samples = 1000
    
    # Generate mock predictions and prices
    predictions = []
    prices = []
    timestamps = []
    
    base_price = 50000
    current_price = base_price
    
    for i in range(n_samples):
        # Generate mock prediction
        signal = np.random.choice(['LONG', 'SHORT', 'NEUTRAL'], p=[0.3, 0.3, 0.4])
        confidence = np.random.uniform(0.5, 0.9)
        
        predictions.append({
            'signal': signal,
            'confidence': confidence,
            'probabilities': {
                'long': 0.4 if signal == 'LONG' else 0.2,
                'short': 0.4 if signal == 'SHORT' else 0.2,
                'neutral': 0.4 if signal == 'NEUTRAL' else 0.2
            }
        })
        
        # Generate mock price movement
        price_change = np.random.normal(0, 0.02)  # 2% volatility
        current_price *= (1 + price_change)
        prices.append(current_price)
        
        # Generate timestamp
        timestamp = datetime.now() - timedelta(days=n_samples-i)
        timestamps.append(timestamp)
    
    # Run backtest
    evaluator = ModelEvaluator()
    backtest_results = evaluator.backtester.run_backtest(
        predictions, prices, timestamps, 'BTC'
    )
    
    # Mock model metrics
    model_metrics = {
        'accuracy': 0.75,
        'precision': 0.72,
        'recall': 0.68,
        'f1_score': 0.70,
        'roc_auc': 0.78,
        'confusion_matrix': [[200, 50], [40, 210]]
    }
    
    # Generate report
    report = evaluator.generate_performance_report(backtest_results, model_metrics)
    print(report)
    
    # Save report
    with open('performance_report.md', 'w') as f:
        f.write(report)
    print("📁 Performance report saved to: performance_report.md")
    
    # Create visualizations
    print("📈 Creating performance visualizations...")
    evaluator.create_visualizations(backtest_results, evaluator.backtester.trades)
    print("📁 Performance chart saved to: crypto_rocket_performance.png")

if __name__ == "__main__":
    main()
