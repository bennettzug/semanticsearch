from selectolax.parser import HTMLParser
import httpx
from dataclasses import dataclass

# import re
import csv


@dataclass
class Course:
    subject: str
    number: str
    name: str
    description: str
    credit_hours: str


def make_subjects_dict() -> dict[str, str]:
    url = "https://catalog.ncsu.edu/course-descriptions/"
    response = httpx.get(url)
    html = HTMLParser(response.text)
    subjects = {}
    links = html.css("#textcontainer > div > ul > li > a")
    for link in links:
        subject = link.text()
        href = link.attributes["href"]
        subjects[subject] = href
    return subjects


def get_courses(subjects: dict):
    results = []
    n = 0
    for subject, href in subjects.items():
        response = httpx.get("https://catalog.ncsu.edu" + href)
        html = HTMLParser(response.text)
        courses = html.css("#textcontainer > div > div")

        for course in courses:
            # print(course.text() + "\n\n")
            subjectandnumber = course.css_first(
                "span.text.detail-coursecode.text--semibold"
            ).text()
            subjectandnumber = subjectandnumber.split("/")[0]
            subject = subjectandnumber.split()[0]
            number = subjectandnumber.split()[1]
            name = course.css_first(
                "span.text.detail-title.margin--tiny.text--semibold"
            ).text()
            hours = course.css_first("span.text.detail-hours_html").text()
            hours = hours.strip("()").split(" ")[0]
            try:
                description = course.css_first("div > p").text()
            except AttributeError:
                description = ""
            course = Course(subject, number, name, description, hours)
            results.append(course)
        n += 1
        print(f"finished with {subject} ({n}/{len(subjects)})")
    return results


def main():
    subjects = make_subjects_dict()
    results = get_courses(subjects)
    with open("NCSU_courses.csv", "w", newline="") as csvfile:
        # clear file
        csvfile.truncate()

        writer = csv.writer(csvfile)
        writer.writerow(["subject", "number", "name", "description", "credits"])
        for course in results:
            writer.writerow(
                [
                    course.subject,
                    course.number,
                    course.name,
                    course.description,
                    course.credit_hours,
                ]
            )


if __name__ == "__main__":
    main()
