# API Style Guide

This document outlines REST API design guidelines for the muzikki-backend project.

## General Principles

- Follow RESTful conventions
- Use JSON for request and response bodies
- Use proper HTTP methods and status codes
- Implement versioning for the API

## URL Structure

- Use lowercase letters and hyphens (kebab-case)
- Use nouns for resource names, not verbs
- Use plural nouns for collections

Good:
```
GET /api/v1/artists
GET /api/v1/artists/123
GET /api/v1/artists/123/albums
```

Bad:
```
GET /api/v1/getArtists
GET /api/v1/artist/123
GET /api/v1/artists-albums
```

## HTTP Methods

- **GET**: Retrieve resource(s)
- **POST**: Create a new resource
- **PUT**: Update entire resource (all fields)
- **PATCH**: Partial update of resource
- **DELETE**: Remove resource

## HTTP Status Codes

Use appropriate status codes:

- **200 OK**: Successful GET, PUT, PATCH, or DELETE
- **201 Created**: Successful POST (include Location header)
- **204 No Content**: Successful DELETE with no response body
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource doesn't exist
- **500 Internal Server Error**: Server error

## Request/Response Format

### Success Response Example

```json
{
  "id": 1,
  "name": "Artist Name",
  "bio": "Artist biography",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### List Response Example

```json
{
  "count": 100,
  "next": "https://api.example.com/api/v1/artists?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Artist 1"
    },
    {
      "id": 2,
      "name": "Artist 2"
    }
  ]
}
```

### Error Response Example

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "name": ["This field is required."],
      "email": ["Enter a valid email address."]
    }
  }
}
```

## Pagination

- Use limit/offset or page-based pagination
- Include pagination metadata in responses
- Set reasonable default limits (e.g., 20-50 items)

Example:
```
GET /api/v1/artists?page=2&limit=20
```

## Filtering and Sorting

- Use query parameters for filtering
- Use consistent naming for sort parameters

Examples:
```
GET /api/v1/artists?genre=rock
GET /api/v1/artists?sort=-created_at  # Descending
GET /api/v1/artists?sort=name         # Ascending
```

## Authentication

- Use token-based authentication (JWT recommended)
- Include authentication token in Authorization header
- Implement refresh token mechanism

Example:
```
Authorization: Bearer <token>
```

## Versioning

- Include version in URL path: `/api/v1/`
- Maintain backward compatibility when possible
- Clearly document breaking changes

## Field Naming

- Use snake_case for JSON fields
- Be consistent with naming across all endpoints
- Use clear, descriptive field names

Example:
```json
{
  "user_id": 1,
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Documentation

- Document all API endpoints
- Include request/response examples
- Document authentication requirements
- Use tools like Swagger/OpenAPI for interactive documentation
