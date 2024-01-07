#!/usr/local/bin/python3

import os
import shutil
import json
import fitz


def __prt__(msg, lvl):
    formatted = ""
    if lvl == "GOOD":
        formatted += "\033[1;32;40m[A]\033[0;37;49m "
    elif lvl == "MAYBE":
        formatted += "\033[1;33;40m[A]\033[0;37;49m "
    elif lvl == "WARN":
        formatted += "\033[1;31;40m[A]\033[0;37;49m "
    else:
        raise RuntimeError(f"\033[1;31;40m [A] \033[0;37;40m Unrecognized prt level: {lvl}")

    return formatted + msg


def good(msg):
    return __prt__(msg, "GOOD")


def maybe(msg):
    return __prt__(msg, "MAYBE")


def warn(msg):
    return __prt__(msg, "WARN")


def run_plastex(args, target):
    print(maybe(f"Running plasTeX with target {target} and the following args:"))
    plastex_args = " "
    for arg in args:
        print(f"    {arg}")
        plastex_args += arg + " "
    cmd = "plastex" + plastex_args + f" -- {target}"
    os.system(cmd)


def run_latexmk(args, target):
    print(maybe(f"Running latexmk with target {target} and the following args:"))
    latexmk_args = " "
    for arg in args:
        print(f"    {arg}")
        latexmk_args += arg + " "
    cmd = "latexmk" + latexmk_args + f"{target}"
    os.system(cmd)


def gen_algos(gen_dir, post):
    # copy template/algos/style.sty, algo.sty, latexmkrc
    stys = ["algo", "style", "ntabbing"]
    for sty in stys:
        shutil.copy(f"template/algos/{sty}.sty", f"posts/{post}/algos/")
    print(maybe(f"[Building algorithm pngs for {post}"))

    # for algo_name.tex in algos/
    # ends in .tex
    algos = [algo[:-4] for algo in next(os.walk(f"posts/{post}/algos"))[2] if algo.endswith(".tex")]
    print(maybe("Building the following algorithm pngs:"))
    for algo_name in algos:
        print(f"    {algo_name}")
    for algo_name in algos:
        # TODO: don't change directories
        os.chdir(f"posts/{post}/algos")

        print(maybe(f"Building png for algorithm {post}/algos/{algo_name}.tex"))

        # algo_name.tex -> algo_name.pdf
        # NOTE: --outdir is relative to -cd
        print(maybe(f"Making temporary directory for algo {algo_name} generation"))
        os.mkdir("temp")

        target = f"{algo_name}.tex"
        args = [
            "-pdf",
            "-quiet",
            "-outdir=temp/",
        ]
        run_latexmk(args, target)

        # TODO better error checking
        if not os.path.exists(f"temp/{algo_name}.pdf"):
            raise RuntimeError(warn(f"temp/{algo_name}.pdf was not built successfully"))
        print(good(f"Successfully generated temp/{algo_name}.pdf"))

        # algo_name.pdf -> algo_name-crop.pdf
        cmd = f"pdfcrop temp/{algo_name}.pdf"
        os.system(cmd)
        print(good(f"Cropped temp/{algo_name}.pdf"))

        # algo_name-crop.pdf -> algo_name.png
        with fitz.open(f"temp/{algo_name}-crop.pdf") as cropped:
            for page in cropped:
                pix = page.get_pixmap(dpi=300)
                pix.save(f"{algo_name}.png")
        print(good(f"Converted cropped pdf to {algo_name}.png"))

        # TODO: don't change directories
        os.chdir("../../..")

        shutil.move(f"posts/{post}/algos/{algo_name}.png", f"posts/{post}/{algo_name}.png")
        print(good(f"Moved {algo_name}.png to posts/{post}"))

        shutil.rmtree(f"posts/{post}/algos/temp")
        # TODO: remove generated png?
        print(good(f"Cleaned up generated files for algos/{algo_name}"))

    stys = ["algo", "style", "ntabbing"]
    for sty in stys:
        os.remove(f"posts/{post}/algos/{sty}.sty")
    print(good(f"Removed .sty files from posts/{post}"))


def clean_post(post):
    print(maybe(f"Cleaning up html files for {post}"))
    shutil.rmtree(f"posts/{post}/main/")
    os.remove(f"posts/{post}/{post}-templated.html")
    print(good(f"Did clean up for {post}"))


def clean_pdf(post):
    print(maybe(f"Cleaning up pdf files for {post}"))
    shutil.rmtree(f"posts/{post}/temp/")
    print(good(f"Did clean up for {post}"))

def gen_pdf(gen_dir, post):
    # TODO: don't change directories
    os.chdir(f"posts/{post}/")
    os.mkdir("temp")

    target = "main.tex"
    args = [
        "-pdf",
        "-quiet",
        "-outdir=temp/",
    ]
    run_latexmk(args, target)

    # TODO better error checking
    if not os.path.exists("temp/main.pdf"):
        raise RuntimeError(warn("temp/main.pdf was not built successfully"))
    print(good("Successfully generated temp/main.pdf"))

    # TODO: don't change directories
    os.chdir("../..")

def posts(gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(warn(f"{gen_dir}/ does not exist. Build main site first"))

    print(maybe("Building posts"))
    os.mkdir(f"{gen_dir}/posts/")
    # Each folder in posts/ is a post
    # The only required file is main.tex, the post
    # Any other tex files, as far as this function is concerned, do not exist

    # template/ contains three files
    # posts-commgroup.css
    #   This is the style sheet for every post, to maintain a unified style
    # posts-start.html
    #   The first part of the blog template
    # posts-end.html
    #   The last part of the blog template
    # Upon rendering a post into a fragment, we concatenate the results

    # Copy posts-commgroup.css into main/posts/
    shutil.copy("template/posts-commgroup.css", f"{gen_dir}/styles/")
    print(good("Copied posts-commgroup.css"))

    # Render each post
    posts = next(os.walk("posts/"))[1]
    for post in posts:
        print(maybe(f"Building post {post}"))
        if not os.path.isfile(f"posts/{post}/main.tex"):
            raise RuntimeError(warn(f"posts/{post}/main.tex does not exist, no post to build"))

        # Generate algo SVGs if they exist
        if os.path.exists(f"posts/{post}/algos"):
            gen_algos(gen_dir, post)

        # Render post fragment
        args = [
            "--theme=fragment",
            "--split-level=-1",
            f"--dir=posts/{post}/main/",
            f"--image-filenames='{post}-images/$num'",
            f"--filename={post}",
            "--packages-dir=pkgs",
        ]
        target = f"posts/{post}/main.tex"
        run_plastex(args, target)
        print(good(f"Built fragment for {post}"))

        if not os.path.exists(f"posts/{post}/meta.json"):
            raise RuntimeError(warn(f"posts/{post}/meta.json does not exist, cannot get title"))
        with open(f"posts/{post}/meta.json", "r") as meta_data:
            meta = json.load(meta_data)

        # Assemble template
        with open(f"posts/{post}/{post}-templated.html", "w") as curr_post:
            with open("template/posts-start.html", "r") as start:
                for line in start:
                    if line == "</head>\n":
                        curr_post.write(f"<title>{meta['title']}</title>")
                    curr_post.write(line)
            curr_post.write("\n")

            with open(f"posts/{post}/main/{post}.html", "r") as content:
                for line in content:
                    curr_post.write(line)
            curr_post.write("\n")

            with open("template/posts-end.html", "r") as end:
                for line in end:
                    curr_post.write(line)
            curr_post.write("\n")

        print(good(f"Wrote {post} to full file"))
        # Copy everything to gen_dir
        shutil.copy(f"posts/{post}/{post}-templated.html", f"{gen_dir}/posts/{post}.html")
        if os.path.exists(f"posts/{post}/main/{post}-images"):
            shutil.copytree(f"posts/{post}/main/{post}-images", f"{gen_dir}/posts/{post}-images")

        gen_pdf(gen_dir, post)
        # Copy everything to gen_dir
        shutil.copy(f"posts/{post}/temp/main.pdf", f"{gen_dir}/posts/{post}.pdf")

        # Remove generated files for post
        clean_post(post)
        clean_pdf(post)

    print(good("Built all posts"))


def fix_title_front(gen_dir, target_file, title):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(warn(f"{gen_dir}/ does not exist. Build main site first"))

    with open(f"{gen_dir}/{target_file}_fixed.html", "w") as idx_out:
        with open(f"{gen_dir}/{target_file}.html", "r") as idx_in:
            for line in idx_in:
                if "<title>" in line:
                    idx_out.write(f"<title>{title}</title>\n")
                else:
                    idx_out.write(line)
    os.remove(f"{gen_dir}/{target_file}.html")
    shutil.move(f"{gen_dir}/{target_file}_fixed.html", f"{gen_dir}/{target_file}.html")
    print(good(f"Fixed title of {target_file}.html"))


def clean_main(root_file, gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(warn(f"{gen_dir}/ does not exist. Build main site first"))

    # # remove unused CSS
    # os.remove(f"{gen_dir}/styles/theme-green.css")
    # os.remove(f"{gen_dir}/styles/theme-white.css")
    # os.remove(f"{gen_dir}/styles/theme-blue.css")

    if os.path.exists(f"{root_file}.paux"):
        os.remove(f"{root_file}.paux")
    if os.path.exists(".auctex-auto/"):
        shutil.rmtree(".auctex-auto/")

    print(good("Cleaned up files"))


def build_main(root_file, gen_dir):
    print(maybe("Building main files"))

    args = [
        "--extra-templates=template/commgrp",
        "--theme=commgrp",
        "--extra-css theme-commgroup.css",
        "--no-display-toc",
        "--filename='index [$title]'",
        "--split-level=-1",
        f"--dir={gen_dir}",
    ]
    target = f"{root_file}.tex"
    run_plastex(args, target)

    fix_title_front(gen_dir, "index", "commutative.group")
    fix_title_front(gen_dir, "About", "About")
    fix_title_front(gen_dir, "All-Posts", "All Posts")

    # TODO: These should be automatically copied...
    print(maybe(f"Copying template files to {gen_dir}/"))
    shutil.copy("template/commgrp/symbol-defs.svg", f"{gen_dir}/symbol-defs.svg")

    if not os.path.exists(f"{gen_dir}/js/"):
        raise RuntimeError(warn(f"No js/ folder in {gen_dir}"))
    js = ["jquery.min", "plastex", "svgxuse"]
    for js_file in js:
        shutil.copy(f"template/commgrp/js/{js_file}.js", f"{gen_dir}/js/{js_file}.js")
    print(good("Copied template files"))

    print(good("Built Main Site"))


def fresh(gen_dir):
    if os.path.exists(gen_dir):
        print(maybe("Cleaning old generated directory"))

        print(maybe("Removing .html files"))
        html = [
            html_file[:-5]
            for html_file in next(os.walk(f"{gen_dir}"))[2]
            if html_file.endswith(".html")
        ]
        for html_file in html:
            os.remove(f"{gen_dir}/{html_file}.html")

        print(maybe("Removing .svg file"))
        os.remove(f"{gen_dir}/symbol-defs.svg")

        print(maybe("Removing folders"))
        shutil.rmtree(f"{gen_dir}/js/")
        shutil.rmtree(f"{gen_dir}/posts/")
        shutil.rmtree(f"{gen_dir}/styles/")

        print(good("Cleaned old generated directory"))


def check(root_file):
    print(maybe("Checking for necessary files"))
    if not os.path.exists(f"{root_file}.tex"):
        raise RuntimeError(warn(f"Root file {root_file}.tex not found"))
    if not os.path.exists("posts/"):
        raise RuntimeError(warn("Posts folder posts not found"))
    if not os.path.exists("template/"):
        raise RuntimeError(warn("Templates folder templates/ not found"))
    else:
        post_templates = ["posts-commgroup.css", "posts-start.html", "posts-start.html"]
        print(maybe("Checking for the following template files for posts:"))
        for temp in post_templates:
            print(f"    {temp}")
        for temp in post_templates:
            if not os.path.exists(f"template/{temp}"):
                raise RuntimeError(warn(f"{temp} does not exist in template/"))
        print(good("Found template files"))

        if not os.path.exists("template/algos/"):
            raise RuntimeError(warn("algos/ does not exist in template/"))
        stys = ["algo", "style", "ntabbing"]
        print(maybe("Checking for the following .sty files for algos:"))
        for sty in stys:
            print(f"    {sty}.sty")
        for sty in stys:
            if not os.path.exists(f"template/algos/{sty}.sty"):
                raise RuntimeError(warn(f"{sty}.sty does not exist in template/algos/"))

        if not os.path.exists("template/commgrp/"):
            raise RuntimeError(warn("commgrp/ does not exist in template/"))
        # TODO: These should be automatically copied...
        templates = ["default-layout.jinja2", "document-layout.jinja2", "symbol-defs.svg"]
        print(maybe("Checking for the following template files in template/commgrp:"))
        for temp in templates:
            print(f"    {temp}")
        for temp in templates:
            if not os.path.exists(f"template/commgrp/{temp}"):
                raise RuntimeError(warn(f"{temp} does not exist in template/commgrp/"))

        if not os.path.exists("template/commgrp/js/"):
            raise RuntimeError(warn("commgrp/js/ does not exist in template/"))
        js = ["jquery.min", "plastex", "svgxuse"]
        print(maybe("Checking for the following .js files in template/commgrp/js:"))
        for js_file in js:
            print(f"    {js_file}.js")
        for js_file in js:
            if not os.path.exists(f"template/commgrp/js/{js_file}.js"):
                raise RuntimeError(warn(f"{js_file}.js does not exist in template/commgrp/js/"))

    print(good("Found all necessary files"))


def main():
    root_file = "main"
    gen_dir = "gen"

    check(root_file)
    fresh(gen_dir)
    build_main(root_file, gen_dir)
    posts(gen_dir)
    clean_main(root_file, gen_dir)


if __name__ == "__main__":
    main()
