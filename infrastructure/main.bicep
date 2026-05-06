@description('Location for all resources')
param location string = resourceGroup().location

@description('SQL Server admin username')
param sqlAdminUsername string = 'sqladmin'

@description('SQL Server admin password')
@minLength(8)
@secure()
param sqlAdminPassword string

@description('App Service Plan name')
param appServicePlanName string = 'banking-plan-${uniqueString(resourceGroup().id)}'

@description('Web App name')
param webAppName string = 'banking-app-${uniqueString(resourceGroup().id)}'

@description('SQL Server name')
param sqlServerName string = 'banking-sql-${uniqueString(resourceGroup().id)}'

@description('Key Vault name')
param keyVaultName string = 'banking-kv-${uniqueString(resourceGroup().id)}'

@description('Database name')
param databaseName string = 'bankingdb'

// ========== Key Vault ==========

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// ========== SQL Database ==========

resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminUsername
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: '1.2'
  }
}

// Allow Azure Services to access SQL Server
resource sqlServerFirewallRule 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Allow local development
resource sqlServerLocalRule 'Microsoft.Sql/servers/firewallRules@2023-05-01-preview' = {
  parent: sqlServer
  name: 'AllowLocal'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '255.255.255.255'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: databaseName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
    capacity: 5
  }
  properties: {
    maxSizeBytes: 2147483648
    collation: 'SQL_Latin1_General_CP1_CI_AS'
  }
}

// ========== App Service Plan & Web App ==========

resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
    capacity: 1
  }
  properties: {
    reserved: true // For Linux
  }
  kind: 'linux'
}

resource webApp 'Microsoft.Web/sites@2023-01-01' = {
  name: webAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      http20Enabled: true
      minTlsVersion: '1.2'
      appSettings: [
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
      ]
    }
  }
}

// Store SQL connection string in Key Vault
resource sqlConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SqlConnectionString'
  properties: {
    value: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Initial Catalog=${databaseName};Persist Security Info=False;User ID=${sqlAdminUsername};Password=${sqlAdminPassword};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'
  }
}

// Store JWT Secret in Key Vault
resource jwtSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'JwtSecret'
  properties: {
    value: uniqueString(resourceGroup().id, subscription().subscriptionId, 'jwt-secret-key')
  }
}

// ========== RBAC: Grant Web App access to Key Vault ==========

@description('Role ID for Key Vault Secrets Officer')
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86a0e88'

resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, webApp.id, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ========== Outputs ==========

@description('Web App URL')
output webAppUrl string = 'https://${webApp.properties.defaultHostName}'

@description('SQL Server FQDN')
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName

@description('SQL Database Name')
output databaseName string = databaseName

@description('Key Vault URI')
output keyVaultUri string = keyVault.properties.vaultUri

@description('Key Vault Name')
output keyVaultName string = keyVault.name

@description('Deployment completed successfully')
output deploymentStatus string = 'Ready for deployment. Run: az webapp deployment source config-zip -g ${resourceGroup().name} -n ${webAppName} --src banking-app.zip'

