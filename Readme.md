# Code Snippets for learn.livinglabs.network

This repository contains a collection of code snippets designed to enhance the functionality of a Ghost-based website. These snippets provide features like course filtering, interactive timelines, a global glossary, and general-purpose post filtering.

## Overall Structure

The repository is organized into the following directories:

-   **Course List**: Contains the code for a filterable course list.
-   **Timeline**: Includes the necessary files to generate an interactive timeline.
-   **Global**: Holds snippets that are intended to be used globally across the site, such as the glossary.
-   **FAQ**: Contains the code for a FAQ section.
-   **Fungal**: Contains the code for a variable font.
-   **TOC**: Contains the code for a table of contents.

## Course List Filter

This feature allows users to filter a list of courses based on various attributes.

**Functionality:**

-   Fetches course data from the Ghost API.
-   Filters courses by tags, which are parsed in a `keyword-value` format (e.g., `#level-beginner`).
-   Active filters are "course"/"#course" and "Active".
-   Displays the filtered results in a grid layout.

**Files:**

-   `Course List/Ghost/filterhtml.html`: The HTML structure for the filter interface and the course list.
-   `Course List/Ghost/filterjs.html`: The JavaScript that handles the API requests, filtering logic, and DOM manipulation.
-   `Course List/Ghost/filtercss.html`: The CSS for styling the filter and the course list.

**To-Do:**

- [x]  Add filter priority.

## Timeline

This snippet uses the Knight Lab's Timeline.js library to create an interactive, chronological timeline of events.

**Functionality:**

-   Loads timeline data from a JSON file.
-   Renders an interactive timeline with navigation and zoom features.
-   Includes an auto-scroll feature that advances through the timeline slides automatically.

**Files:**

-   `Timeline/Ghost Snippets/main.html`: The basic HTML structure to embed the timeline.
-   `Timeline/Ghost Snippets/mainjs.html`: The JavaScript that initializes the timeline, loads the data, and implements the auto-scroll functionality.
-   `2025-2026_timeline.json`: The data file for the timeline in JSON format.
-   `Timeline/csv-to-timeline-json.py`: A Python script to convert a CSV file to the required JSON format.

**To-Do:**

-   Visual separation for courses in the same School that run for the same duration.

## Global Snippets

These snippets are designed to be included in the global code injection of a Ghost site to provide site-wide functionality.

### Glossary

This feature automatically creates tooltips for predefined terms throughout the website.

**Functionality:**

-   Loads a dictionary of terms and definitions from a JSON file.
-   Scans the text content of the page and wraps the defined terms in a `<span>` tag.
-   Uses Tippy.js to display a tooltip with the definition when a user hovers over a term.

**Files:**

-   `Global/glossary.html`: The HTML and JavaScript code to load the dictionary, parse the content, and initialize the tooltips.
-   `Global/glossary.json`: The JSON file containing the dictionary of terms and definitions.

### General Purpose Filtered Posts

This is a flexible script that allows you to display a filtered list of posts anywhere on your site.

**Functionality:**

-   Fetches posts from the Ghost API based on a set of tags.
-   Supports both "AND" and "OR" logic for tag filtering.
-   Includes a "Load More" button to paginate through the results.
-   Can be configured to have multiple instances on the same page.

**Files:**

-   `Global/General Purpose Filtered Posts/GPFPhtml.html`: The HTML structure for the filter configuration and the post container.
-   `Global/General Purpose Filtered Posts/GPFPjs.html`: The JavaScript that handles the API requests, filtering, and "Load More" functionality.
-   `Global/General Purpose Filtered Posts/GPFPcss.html`: The CSS for styling the filtered posts.
