"""
Indonesia Input-Output Analysis Module
Data source: Indonesia Input-Output Tables 2000-2022 (BPS)
Provides input-output analysis capabilities including:
- Technical coefficients matrix
- Leontief inverse matrix
- Output multipliers
- Impact analysis for infrastructure projects
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import json


class InputOutputAnalyzer:
    """Class for conducting Input-Output economic analysis"""
    
    def __init__(self, excel_path: str = 'indonesia-tables-as-of-june-2023.xlsx'):
        self.excel_path = excel_path
        self.data = {}
        self.industry_names = []
        self.A_matrix = None
        self.leontief_inverse = None
        self.total_output = None
        self.intermediate_transactions = None
        
    def load_table(self, year: int = 2020) -> bool:
        """
        Load Input-Output table for specified year
        
        Args:
            year: Year of IO table (2000, 2007-2022)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            xls = pd.ExcelFile(self.excel_path)
            
            # Map year to sheet name
            year_to_sheet = {
                2000: 'Table 1.1',
                2007: 'Table 1.2',
                2008: 'Table 1.3',
                2009: 'Table 1.4',
                2010: 'Table 1.5',
                2011: 'Table 1.6',
                2012: 'Table 1.7',
                2013: 'Table 1.8',
                2014: 'Table 1.9',
                2015: 'Table 1.10',
                2016: 'Table 1.11',
                2017: 'Table 1.12',
                2018: 'Table 1.13',
                2019: 'Table 1.14',
                2020: 'Table 1.15',
                2021: 'Table 1.16',
                2022: 'Table 1.17'
            }
            
            if year not in year_to_sheet:
                raise ValueError(f"Year {year} not available. Available years: {list(year_to_sheet.keys())}")
            
            sheet = year_to_sheet[year]
            df = pd.read_excel(xls, sheet_name=sheet, header=None)
            
            # Extract industry names from row 4
            self.industry_names = df.iloc[4, 2:37].tolist()
            
            # Get intermediate transaction matrix (rows 6-40, cols 2-36)
            self.intermediate_transactions = df.iloc[6:41, 2:37].values.astype(float)
            
            # Get total output from row 49 "TOTAL"
            self.total_output = df.iloc[49, 2:37].values.astype(float)
            
            # Calculate technical coefficients
            self._calculate_technical_coefficients()
            
            # Calculate Leontief inverse
            self._calculate_leontief_inverse()
            
            self.data['year'] = year
            self.data['total_output_sum'] = float(self.total_output.sum())
            
            return True
            
        except Exception as e:
            print(f"Error loading IO table: {e}")
            return False
    
    def _calculate_technical_coefficients(self):
        """Calculate direct technical coefficients matrix A"""
        n = len(self.industry_names)
        self.A_matrix = np.zeros_like(self.intermediate_transactions, dtype=float)
        
        for j in range(n):
            if self.total_output[j] > 0:
                self.A_matrix[:, j] = self.intermediate_transactions[:, j] / self.total_output[j]
    
    def _calculate_leontief_inverse(self):
        """Calculate Leontief inverse matrix (I-A)^(-1)"""
        n = len(self.industry_names)
        I = np.eye(n)
        self.leontief_inverse = np.linalg.inv(I - self.A_matrix)
    
    def get_output_multipliers(self) -> Dict[str, float]:
        """
        Calculate output multipliers for all sectors
        
        Returns:
            Dictionary mapping sector names to their output multipliers
        """
        if self.leontief_inverse is None:
            return {}
        
        multipliers = self.leontief_inverse.sum(axis=0)
        return {name: float(mult) for name, mult in zip(self.industry_names, multipliers)}
    
    def get_top_sectors_by_multiplier(self, n: int = 10) -> list:
        """
        Get top N sectors by output multiplier
        
        Args:
            n: Number of top sectors to return
            
        Returns:
            List of tuples (sector_name, multiplier)
        """
        multipliers = self.get_output_multipliers()
        sorted_sectors = sorted(multipliers.items(), key=lambda x: x[1], reverse=True)
        return sorted_sectors[:n]
    
    def calculate_impact(self, final_demand_change: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate total economic impact of a change in final demand
        
        Args:
            final_demand_change: Dictionary mapping sector names to demand changes (in $ million)
            
        Returns:
            Dictionary with total output impact per sector
        """
        if self.leontief_inverse is None:
            return {}
        
        # Create final demand change vector
        fd_vector = np.zeros(len(self.industry_names))
        for i, name in enumerate(self.industry_names):
            if name in final_demand_change:
                fd_vector[i] = final_demand_change[name]
        
        # Calculate total output impact: ΔX = (I-A)^(-1) * ΔF
        output_impact = np.dot(self.leontief_inverse, fd_vector)
        
        return {name: float(impact) for name, impact in zip(self.industry_names, output_impact)}
    
    def calculate_infrastructure_impact(self, investment_amount: float, 
                                       sector: str = 'Construction') -> Dict:
        """
        Calculate economic impact of infrastructure investment
        
        Args:
            investment_amount: Investment amount in $ million
            sector: Target sector for investment (default: Construction)
            
        Returns:
            Dictionary with detailed impact analysis
        """
        if sector not in self.industry_names:
            return {'error': f'Sector {sector} not found'}
        
        # Create final demand shock
        fd_change = {sector: investment_amount}
        
        # Calculate direct and indirect impacts
        output_impact = self.calculate_impact(fd_change)
        
        total_impact = sum(output_impact.values())
        direct_impact = investment_amount
        indirect_impact = total_impact - direct_impact
        
        # Calculate multiplier effect
        multiplier = total_impact / direct_impact if direct_impact > 0 else 0
        
        return {
            'investment_sector': sector,
            'investment_amount': investment_amount,
            'direct_impact': direct_impact,
            'indirect_impact': indirect_impact,
            'total_impact': total_impact,
            'multiplier': multiplier,
            'sector_breakdown': output_impact,
            'top_5_beneficiaries': sorted(output_impact.items(), 
                                          key=lambda x: x[1], reverse=True)[:5]
        }
    
    def get_sector_linkages(self, sector: str) -> Dict:
        """
        Analyze backward and forward linkages for a sector
        
        Args:
            sector: Sector name to analyze
            
        Returns:
            Dictionary with linkage analysis
        """
        if sector not in self.industry_names or self.A_matrix is None:
            return {}
        
        idx = self.industry_names.index(sector)
        
        # Backward linkage (power of dispersion)
        # Sum of column in Leontief inverse
        backward_linkage = self.leontief_inverse[:, idx].sum()
        
        # Forward linkage (sensitivity of dispersion)
        # Sum of row in Leontief inverse
        forward_linkage = self.leontief_inverse[idx, :].sum()
        
        # Direct inputs from other sectors (column sum of A matrix)
        direct_inputs = self.A_matrix[:, idx].sum()
        
        # Direct sales to other sectors (row sum of A matrix)
        direct_sales = self.A_matrix[idx, :].sum()
        
        return {
            'sector': sector,
            'backward_linkage': float(backward_linkage),
            'forward_linkage': float(forward_linkage),
            'direct_input_coefficient': float(direct_inputs),
            'direct_sales_coefficient': float(direct_sales),
            'interpretation': self._interpret_linkages(backward_linkage, forward_linkage)
        }
    
    def _interpret_linkages(self, backward: float, forward: float) -> str:
        """Interpret linkage values"""
        avg_linkage = len(self.industry_names) ** 0.5  # Rough average benchmark
        
        if backward > avg_linkage and forward > avg_linkage:
            return "Key sector - strong backward and forward linkages"
        elif backward > avg_linkage:
            return "Base industry - strong backward linkages, drives upstream sectors"
        elif forward > avg_linkage:
            return "Strategic sector - strong forward linkages, enables downstream activities"
        else:
            return "Standard sector - moderate linkages"
    
    def export_to_json(self, filename: str = 'io_analysis_results.json'):
        """Export analysis results to JSON file"""
        results = {
            'year': self.data.get('year'),
            'total_output': float(self.total_output.sum()) if self.total_output is not None else None,
            'sectors': self.industry_names,
            'output_multipliers': self.get_output_multipliers(),
            'top_sectors': self.get_top_sectors_by_multiplier(10)
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return filename


def create_io_summary() -> Dict:
    """Create a summary of Indonesia IO table analysis"""
    analyzer = InputOutputAnalyzer()
    
    if not analyzer.load_table(2020):
        return {'error': 'Failed to load IO table'}
    
    summary = {
        'year': 2020,
        'total_output_million_usd': analyzer.data['total_output_sum'],
        'num_sectors': len(analyzer.industry_names),
        'sectors': analyzer.industry_names,
        'top_multipliers': analyzer.get_top_sectors_by_multiplier(10),
        'all_multipliers': analyzer.get_output_multipliers()
    }
    
    return summary


if __name__ == '__main__':
    # Run example analysis
    print("=== INDONESIA INPUT-OUTPUT ANALYSIS ===\n")
    
    analyzer = InputOutputAnalyzer()
    
    if analyzer.load_table(2020):
        print(f"Loaded 2020 IO Table")
        print(f"Total Output: ${analyzer.data['total_output_sum']:,.2f} million USD\n")
        
        print("=== TOP 10 SECTORS BY OUTPUT MULTIPLIER ===")
        for rank, (sector, mult) in enumerate(analyzer.get_top_sectors_by_multiplier(10), 1):
            print(f"{rank:2d}. {sector}: {mult:.4f}")
        
        print("\n=== INFRASTRUCTURE INVESTMENT IMPACT ($1 Billion) ===")
        impact = analyzer.calculate_infrastructure_impact(1000, 'Construction')
        print(f"Direct Impact: ${impact['direct_impact']:,.2f} million")
        print(f"Indirect Impact: ${impact['indirect_impact']:,.2f} million")
        print(f"Total Impact: ${impact['total_impact']:,.2f} million")
        print(f"Multiplier: {impact['multiplier']:.4f}")
        
        print("\n=== CONSTRUCTION SECTOR LINKAGES ===")
        linkages = analyzer.get_sector_linkages('Construction')
        print(f"Backward Linkage: {linkages['backward_linkage']:.4f}")
        print(f"Forward Linkage: {linkages['forward_linkage']:.4f}")
        print(f"Interpretation: {linkages['interpretation']}")
