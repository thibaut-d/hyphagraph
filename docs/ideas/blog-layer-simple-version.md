# Feature Draft: Blog Layer (Simple Version)

## Overview

Add a Blog Layer to HyphaGraph to allow users to:

- write
- edit
- delete

free-form blog posts, organized with categories and subcategories, and automatically connected to the graph.

This feature is domain-agnostic and works for:

- scientific notes
- project documentation
- fictional writing
- general thinking

## Core Concept

Introduce a new object:

`BlogPost`

A `BlogPost` is:

- a piece of text (Markdown or plain text)
- organized into categories
- automatically linked to existing entities in the graph

## Categories

Users can organize posts using:

`Category`

- name
- slug
- parent_category (optional)

Supports:

- hierarchical organization
- flexible grouping (e.g. `Research / Biology`, `Story / Chapter 1`)

## Entity Linking (Automatic)

Each entity in HyphaGraph already has:

`Entity`

- name
- slug
- synonyms (terms)

When a `BlogPost` is created or updated:

1. The system scans the text.
2. Matches words and phrases against entity metadata:
   - entity name
   - entity synonyms
3. Automatically generates links to entities.

## Example

Entities:

`Entity: Temple of the One`

Synonyms: `["Temple", "The One", "Unification Temple"]`

BlogPost text:

> The temple was silent when she arrived.

Result:

- `temple` is linked to `Temple of the One`
- no need for explicit `[[link]]`

## Key Features

### 1. Basic CRUD

- create blog post
- edit blog post
- delete blog post

### 2. Category Management

- create category
- create subcategory
- assign posts to categories

### 3. Automatic Entity Detection

- no manual linking required
- works on save
- updates when entities evolve

### 4. Optional Explicit Linking

Users can still write:

`[[Temple of the One]]`

Explicit links override automatic detection.

## Data Model (Simplified)

`BlogPost`

- id
- title
- content
- category_id
- linked_entities[]
- created_at
- updated_at

## Design Principles

- keep it simple
- no forced structure
- no complex taxonomy in the writing layer
- graph remains the source of truth

## Non-Goals

- no advanced writing features (yet)
- no narrative modeling (arcs, scenes, etc.)
- no automatic graph modification from posts

## Benefits

- lightweight writing layer
- no need for external tools
- seamless connection between text and graph
- minimal cognitive load for users

## Summary

This feature adds a simple writing interface on top of HyphaGraph, with:

- categories for organization
- automatic linking to entities
- zero friction for users

It enables writing without sacrificing the structured power of the graph.
