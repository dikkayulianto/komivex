# Komivex Project Context

## Project Information

Project Name: Komivex

Version: 1.0

Status: Development

## Description

Komivex adalah platform baca komik modern yang dibangun menggunakan Laravel dengan arsitektur modular dan dikembangkan menggunakan AI.

## Goals

- Modern UI
- High Performance
- SEO Friendly
- Realtime Scraper
- REST API
- Admin Dashboard
- Multi Source Scraper
- AI Ready

## Technology Stack

Framework: Laravel 12

Language: PHP 8.4

Database: MySQL 8

Cache: Redis

Search: Meilisearch

Queue: Redis Queue

Storage: S3 Compatible

Container: Docker

CI/CD: GitHub Actions

## Architecture

Repository Pattern

Service Pattern

DTO

Event Driven

Observer

Dependency Injection

## Rules

- No SQL Query di Controller
- Business Logic wajib berada di Service
- Gunakan FormRequest
- Gunakan API Resource
- Gunakan PSR-12
- Gunakan SOLID
- Semua fitur harus mudah di-test