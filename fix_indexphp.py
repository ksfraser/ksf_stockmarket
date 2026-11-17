import re

index_path = '/var/www/stockmarket-app/index.php'
with open(index_path, 'r') as f:
    content = f.read()

controller_names = [
    'AuthController',
    'UserController', 
    'StrategyController',
    'AdvisorController',
    'RiskController',
    'SegFundsController',
    'BrokerStopController',
    'AdminSettingsController',
    'TransactionController',
    'ZacksScreenController',
    'DocumentUploadController',
    'ExportController',
    'AlertsController',
    'SharedWithMeController',
    'ATRSweepController',
    'BrokerStopController',
    'FundamentalsController',
    'SymfonyController',
    'PasswordResetController',
    'DocumentUploadController',
    'ExternalAuthController',
]

# Add use statements after existing use block
use_statements = '\n'.join(f'use Ksf\\\\StockMarket\\\\Controller\\\\{c};' for c in controller_names)
# Insert after "use Ksf\\StockMarket\\Security\\AuthStatus;"
insert_after = 'use Ksf\\StockMarket\\Security\\AuthStatus;'
if insert_after in content:
    content = content.replace(
        insert_after,
        insert_after + '\n' + use_statements
    )
    with open(index_path, 'w') as f:
        f.write(content)
    print("Added use statements for", len(controller_names), 'controllers')
else:
    print("ERROR: AuthStatus use statement not found")
    print("Existing use lines:")
    for line in content.split('\n'):
        if line.strip().startswith('use '):
            print(" ", line)
