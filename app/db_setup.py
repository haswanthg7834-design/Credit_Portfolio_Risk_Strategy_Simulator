"""
Database Setup and Management for Credit Portfolio Risk Simulator

This module handles:
- Loading CSV data into SQLite/PostgreSQL database
- Creating optimized tables with proper indexes
- Data validation and quality checks
- Database connection management

Author: Credit Risk Analytics Team
Date: 2024
"""

import pandas as pd
import sqlite3
import sqlalchemy
from sqlalchemy import create_engine, text
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import psycopg2
from psycopg2 import sql
import warnings
warnings.filterwarnings('ignore')

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CreditPortfolioDatabase:
    """
    Database management class for Credit Portfolio Risk Simulator
    """
    
    def __init__(self, db_type: str = 'sqlite', connection_string: Optional[str] = None):
        """
        Initialize database connection
        
        Args:
            db_type: 'sqlite' or 'postgresql'
            connection_string: Custom connection string (optional)
        """
        self.db_type = db_type.lower()
        self.engine = None
        self.connection_string = connection_string
        
        if self.db_type == 'sqlite':
            self._setup_sqlite()
        elif self.db_type == 'postgresql':
            self._setup_postgresql()
        else:
            raise ValueError("db_type must be 'sqlite' or 'postgresql'")
    
    def _setup_sqlite(self):
        """Setup SQLite database connection"""
        if self.connection_string:
            db_path = self.connection_string
        else:
            # Default to local SQLite file
            db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'credit_portfolio.db')
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.connection_string = f'sqlite:///{db_path}'
        self.engine = create_engine(self.connection_string)
        logger.info(f"SQLite database initialized: {db_path}")
    
    def _setup_postgresql(self):
        """Setup PostgreSQL database connection"""
        if not self.connection_string:
            # Default PostgreSQL connection (adjust as needed)
            self.connection_string = "postgresql://postgres:password@localhost:5432/credit_portfolio"
        
        self.engine = create_engine(self.connection_string)
        logger.info("PostgreSQL database connection initialized")
    
    def load_csv_to_database(self, csv_file_path: str, table_name: str, 
                           if_exists: str = 'replace') -> bool:
        """
        Load CSV file into database table
        
        Args:
            csv_file_path: Path to CSV file
            table_name: Target table name
            if_exists: 'fail', 'replace', or 'append'
        
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Loading {csv_file_path} into table '{table_name}'...")
            
            # Read CSV file
            df = pd.read_csv(csv_file_path)
            logger.info(f"Loaded {len(df):,} rows from CSV")
            
            # Data type optimization
            df = self._optimize_datatypes(df)
            
            # Load to database
            df.to_sql(table_name, self.engine, if_exists=if_exists, index=False, method='multi')
            logger.info(f"Successfully loaded {len(df):,} rows into '{table_name}'")
            
            # Create indexes for performance
            self._create_indexes(table_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading CSV to database: {str(e)}")
            return False
    
    def _optimize_datatypes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize pandas datatypes for better database performance
        """
        df_optimized = df.copy()
        
        # Convert object columns that are actually categorical
        categorical_columns = ['acceptance_decision', 'repayment_history', 'income_band', 
                             'region', 'marketing_offer_response', 'risk_segment']
        
        for col in categorical_columns:
            if col in df_optimized.columns:
                df_optimized[col] = df_optimized[col].astype('category')
        
        # Convert float64 to float32 where precision allows
        float_columns = df_optimized.select_dtypes(include=['float64']).columns
        for col in float_columns:
            if col in ['application_score', 'credit_limit', 'balance']:
                # Keep high precision for key financial columns
                continue
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='float')
        
        # Convert int64 to smaller int types where possible
        int_columns = df_optimized.select_dtypes(include=['int64']).columns
        for col in int_columns:
            df_optimized[col] = pd.to_numeric(df_optimized[col], downcast='integer')
        
        return df_optimized
    
    def _create_indexes(self, table_name: str):
        """
        Create database indexes for query performance
        """
        try:
            # Common indexes for the credit portfolio tables
            indexes = {
                'credit_portfolio': [
                    'customer_id',
                    'application_score',
                    'acceptance_decision',
                    'income_band',
                    'region',
                    'delinquency_status'
                ],
                'portfolio_with_risk_metrics': [
                    'customer_id',
                    'risk_segment',
                    'application_score',
                    'risk_score',
                    'delinquency_status'
                ]
            }
            
            if table_name in indexes:
                for column in indexes[table_name]:
                    try:
                        index_name = f"idx_{table_name}_{column}"
                        if self.db_type == 'sqlite':
                            query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column})"
                        else:
                            query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column})"
                        
                        with self.engine.connect() as conn:
                            conn.execute(text(query))
                            conn.commit()
                        logger.info(f"Created index: {index_name}")
                    except Exception as e:
                        logger.warning(f"Could not create index on {column}: {str(e)}")
                        
        except Exception as e:
            logger.warning(f"Error creating indexes: {str(e)}")
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame
        
        Args:
            query: SQL query string
            
        Returns:
            pd.DataFrame: Query results
        """
        try:
            df = pd.read_sql_query(query, self.engine)
            logger.info(f"Query executed successfully, returned {len(df):,} rows")
            return df
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a database table
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Table information
        """
        try:
            # Get row count
            count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            row_count = self.execute_query(count_query)['row_count'].iloc[0]
            
            # Get column information
            if self.db_type == 'sqlite':
                columns_query = f"PRAGMA table_info({table_name})"
            else:
                columns_query = f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
                """
            
            columns_info = self.execute_query(columns_query)
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'columns': columns_info.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error getting table info: {str(e)}")
            return {}
    
    def validate_data_quality(self, table_name: str) -> Dict[str, Any]:
        """
        Run data quality checks on a table
        
        Args:
            table_name: Name of the table to validate
            
        Returns:
            dict: Data quality results
        """
        try:
            quality_results = {}
            
            # Get basic table stats
            table_info = self.get_table_info(table_name)
            quality_results['row_count'] = table_info.get('row_count', 0)
            
            # Check for duplicate customer IDs (if applicable)
            if 'customer_id' in [col.get('name', col.get('column_name', '')) for col in table_info.get('columns', [])]:
                duplicate_query = f"""
                SELECT customer_id, COUNT(*) as count 
                FROM {table_name} 
                GROUP BY customer_id 
                HAVING COUNT(*) > 1
                """
                duplicates = self.execute_query(duplicate_query)
                quality_results['duplicate_customers'] = len(duplicates)
            
            # Check for null values in key columns
            key_columns = ['customer_id', 'application_score', 'credit_limit', 'balance']
            null_counts = {}
            
            for col in key_columns:
                try:
                    null_query = f"SELECT COUNT(*) as null_count FROM {table_name} WHERE {col} IS NULL"
                    null_count = self.execute_query(null_query)['null_count'].iloc[0]
                    null_counts[col] = null_count
                except:
                    continue
            
            quality_results['null_counts'] = null_counts
            
            # Check value ranges for key numeric columns
            numeric_checks = {}
            try:
                range_query = f"""
                SELECT 
                    MIN(application_score) as min_score,
                    MAX(application_score) as max_score,
                    MIN(credit_limit) as min_limit,
                    MAX(credit_limit) as max_limit,
                    MIN(balance) as min_balance,
                    MAX(balance) as max_balance
                FROM {table_name}
                WHERE application_score IS NOT NULL
                """
                ranges = self.execute_query(range_query)
                numeric_checks = ranges.to_dict('records')[0]
            except:
                pass
            
            quality_results['numeric_ranges'] = numeric_checks
            
            logger.info(f"Data quality validation completed for {table_name}")
            return quality_results
            
        except Exception as e:
            logger.error(f"Error in data quality validation: {str(e)}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")


def initialize_credit_portfolio_database(data_directory: str = None, db_type: str = 'sqlite') -> CreditPortfolioDatabase:
    """
    Initialize the credit portfolio database and load all data
    
    Args:
        data_directory: Directory containing CSV files
        db_type: 'sqlite' or 'postgresql'
    
    Returns:
        CreditPortfolioDatabase: Initialized database instance
    """
    if data_directory is None:
        data_directory = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # Initialize database
    db = CreditPortfolioDatabase(db_type=db_type)
    
    # CSV files to load
    csv_files = {
        'credit_portfolio': 'credit_portfolio.csv',
        'portfolio_with_risk_metrics': 'portfolio_with_risk_metrics.csv',
        'risk_segment_summary': 'risk_segment_summary.csv',
        'portfolio_trends_simulation': 'portfolio_trends_simulation.csv'
    }
    
    # Load each CSV file
    for table_name, csv_filename in csv_files.items():
        csv_path = os.path.join(data_directory, csv_filename)
        
        if os.path.exists(csv_path):
            success = db.load_csv_to_database(csv_path, table_name)
            if success:
                logger.info(f"✓ Loaded {table_name}")
                
                # Run data quality validation
                quality_results = db.validate_data_quality(table_name)
                logger.info(f"✓ Data quality check completed for {table_name}")
            else:
                logger.error(f"✗ Failed to load {table_name}")
        else:
            logger.warning(f"CSV file not found: {csv_path}")
    
    return db


if __name__ == "__main__":
    """
    Run database setup as standalone script
    """
    print("Setting up Credit Portfolio Database...")
    
    # Initialize database with CSV data
    db = initialize_credit_portfolio_database()
    
    # Display database information
    print("\n=== DATABASE SETUP COMPLETE ===")
    
    tables = ['credit_portfolio', 'portfolio_with_risk_metrics', 'risk_segment_summary', 'portfolio_trends_simulation']
    
    for table in tables:
        try:
            info = db.get_table_info(table)
            print(f"\nTable: {table}")
            print(f"  Rows: {info.get('row_count', 0):,}")
            print(f"  Columns: {len(info.get('columns', []))}")
        except Exception as e:
            print(f"  Error accessing table {table}: {str(e)}")
    
    # Test a sample query
    try:
        sample_query = """
        SELECT 
            COUNT(*) as total_customers,
            AVG(application_score) as avg_score,
            AVG(credit_limit) as avg_limit,
            COUNT(CASE WHEN delinquency_status > 0 THEN 1 END) * 100.0 / COUNT(*) as delinquency_rate
        FROM credit_portfolio 
        WHERE acceptance_decision = 'Approved'
        """
        results = db.execute_query(sample_query)
        print(f"\n=== PORTFOLIO SUMMARY ===")
        print(f"Total Approved Customers: {results['total_customers'].iloc[0]:,}")
        print(f"Average Credit Score: {results['avg_score'].iloc[0]:.0f}")
        print(f"Average Credit Limit: £{results['avg_limit'].iloc[0]:,.0f}")
        print(f"Delinquency Rate: {results['delinquency_rate'].iloc[0]:.1f}%")
        
    except Exception as e:
        print(f"Error running sample query: {str(e)}")
    
    db.close()
    print("\nDatabase setup complete!")