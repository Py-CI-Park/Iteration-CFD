$ErrorActionPreference = 'Stop'
$env:CFD_DEMO = '1'
$env:CFD_LLM = 'mock'
$env:CFD_PORT = '8807'
$env:CFD_WEB_PORT = '5183'
$env:CFD_WORKSPACE = 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight'
$env:CFD_CONFIG_DIR = 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\research\a321-integration\artifacts\studio-config'
Set-Location -LiteralPath 'D:\Chanil_Park\Project\Programming\Iteration-CFD-a321-preflight\gui'
& npm.cmd run dev
