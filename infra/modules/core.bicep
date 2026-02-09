// ============================================================================
// Core Infrastructure Module - AI Foundry (AI Services) + OpenAI + Search
// ============================================================================
// This uses the AI Services-based approach which allows public network access
// without the data isolation restrictions of Hub-kind workspaces.
// ============================================================================

// Parameters
param location string
param resourceNamePrefix string
param uniqueSuffix string
param principalId string
param principalType string

// Variables
var storageAccountName = replace('st${resourceNamePrefix}${uniqueSuffix}', '-', '')
var openAIAccountName = 'aoai-${resourceNamePrefix}-${uniqueSuffix}'
var searchServiceName = 'search-${resourceNamePrefix}-${uniqueSuffix}'
var foundryResourceName = 'foundry-${resourceNamePrefix}-${uniqueSuffix}'
var projectName = 'proj-${resourceNamePrefix}'
var logAnalyticsName = 'log-${resourceNamePrefix}-${uniqueSuffix}'
var appInsightsName = 'appi-${resourceNamePrefix}-${uniqueSuffix}'

// Role Definition IDs (built-in Azure roles)
var roleDefinitions = {
  cognitiveServicesOpenAIUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
  cognitiveServicesOpenAIContributor: 'a001fd3d-188f-4b5d-821b-7da978bf7442'
  cognitiveServicesContributor: '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'
  cognitiveServicesUser: 'a97b65f3-24c7-4388-baec-2e87135dc908'
  searchIndexDataContributor: '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
  searchIndexDataReader: '1407120a-92aa-4202-b7e9-c0e197c71c8f'
  searchServiceContributor: '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
  storageBlobDataContributor: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  storageBlobDataReader: '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
}

// ============================================================================
// Log Analytics & Application Insights
// ============================================================================
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ============================================================================
// Storage Account (for data and logs)
// ============================================================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: take(storageAccountName, 24)
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource dataContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'data'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// Azure OpenAI Service (Separate resource for model deployments)
// ============================================================================
resource openAIAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: openAIAccountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAIAccountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true // RBAC only - no API keys
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// GPT-4o Model Deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAIAccount
  name: 'gpt-4o'
  sku: {
    name: 'GlobalStandard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// Text Embedding Model Deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openAIAccount
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 30
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
  dependsOn: [gpt4oDeployment]
}

// ============================================================================
// Azure AI Search
// ============================================================================
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: searchServiceName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'free'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ============================================================================
// Azure AI Foundry Resource (AI Services-based)
// ============================================================================
// This uses kind: 'AIServices' which allows public network access
// without the data isolation restrictions of Hub-kind workspaces.
// ============================================================================
resource foundryResource 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: foundryResourceName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: foundryResourceName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true // RBAC only - no API keys
    apiProperties: {
      statisticsEnabled: false
    }

  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ============================================================================
// AI Foundry Project (child of the Foundry resource)
// ============================================================================
resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2024-10-01' = {
  parent: foundryResource
  name: projectName
  location: location
  properties: {
    description: 'LLMOps Workshop Project - Wall-E Electronics RAG Chatbot'
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// ============================================================================
// Connections from Foundry to OpenAI and Search
// ============================================================================
resource aoaiConnection 'Microsoft.CognitiveServices/accounts/connections@2024-10-01' = {
  parent: foundryResource
  name: 'aoai-connection'
  properties: {
    category: 'AzureOpenAI'
    authType: 'AAD'
    isSharedToAll: true
    target: 'https://${openAIAccount.name}.openai.azure.com/'
    metadata: {
      ApiType: 'Azure'
      ResourceId: openAIAccount.id
    }
  }
}

resource searchConnection 'Microsoft.CognitiveServices/accounts/connections@2024-10-01' = {
  parent: foundryResource
  name: 'search-connection'
  properties: {
    category: 'CognitiveSearch'
    authType: 'AAD'
    isSharedToAll: true
    target: 'https://${searchService.name}.search.windows.net/'
    metadata: {
      ResourceId: searchService.id
    }
  }
}

// ============================================================================
// RBAC Role Assignments - User Principal
// ============================================================================

// Cognitive Services OpenAI User - for Azure OpenAI
resource openAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(openAIAccount.id, principalId, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: openAIAccount
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
  }
}

// Cognitive Services OpenAI Contributor - for Azure OpenAI
resource openAIContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(openAIAccount.id, principalId, roleDefinitions.cognitiveServicesOpenAIContributor)
  scope: openAIAccount
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
  }
}

// Cognitive Services User - for AI Foundry
resource foundryUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundryResource.id, principalId, roleDefinitions.cognitiveServicesUser)
  scope: foundryResource
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesUser)
  }
}

// Cognitive Services Contributor - for AI Foundry
resource foundryContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundryResource.id, principalId, roleDefinitions.cognitiveServicesContributor)
  scope: foundryResource
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesContributor)
  }
}

// Search Index Data Contributor - for AI Search
resource searchIndexContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(searchService.id, principalId, roleDefinitions.searchIndexDataContributor)
  scope: searchService
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
  }
}

// Search Service Contributor - for AI Search
resource searchServiceContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(searchService.id, principalId, roleDefinitions.searchServiceContributor)
  scope: searchService
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchServiceContributor)
  }
}

// Storage Blob Data Contributor - for Storage
resource storageBlobContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(storageAccount.id, principalId, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
  }
}

// ============================================================================
// RBAC Role Assignments - Foundry Managed Identity
// ============================================================================

// Foundry needs access to OpenAI
resource foundryToOpenAIRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAIAccount.id, foundryResource.id, roleDefinitions.cognitiveServicesOpenAIContributor)
  scope: openAIAccount
  properties: {
    principalId: foundryResource.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIContributor)
  }
}

// Foundry needs access to Search
resource foundryToSearchRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, foundryResource.id, roleDefinitions.searchIndexDataContributor)
  scope: searchService
  properties: {
    principalId: foundryResource.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataContributor)
  }
}

// Foundry needs access to Storage
resource foundryToStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, foundryResource.id, roleDefinitions.storageBlobDataContributor)
  scope: storageAccount
  properties: {
    principalId: foundryResource.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataContributor)
  }
}

// ============================================================================
// RBAC Role Assignments - Project Managed Identity
// ============================================================================

// Project needs access to OpenAI
resource projectToOpenAIRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAIAccount.id, foundryProject.id, roleDefinitions.cognitiveServicesOpenAIUser)
  scope: openAIAccount
  properties: {
    principalId: foundryProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.cognitiveServicesOpenAIUser)
  }
}

// Project needs access to Search
resource projectToSearchRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(searchService.id, foundryProject.id, roleDefinitions.searchIndexDataReader)
  scope: searchService
  properties: {
    principalId: foundryProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.searchIndexDataReader)
  }
}

// Project needs access to Storage
resource projectToStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, foundryProject.id, roleDefinitions.storageBlobDataReader)
  scope: storageAccount
  properties: {
    principalId: foundryProject.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitions.storageBlobDataReader)
  }
}

// ============================================================================
// Outputs
// ============================================================================
output foundryResourceName string = foundryResource.name
output foundryEndpoint string = 'https://${foundryResource.name}.services.ai.azure.com/'
output projectName string = foundryProject.name
output openAIEndpoint string = 'https://${openAIAccount.name}.openai.azure.com/'
output openAIAccountName string = openAIAccount.name
output searchEndpoint string = 'https://${searchService.name}.search.windows.net/'
output searchServiceName string = searchService.name
output storageAccountName string = storageAccount.name
output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
