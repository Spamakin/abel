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


def clean_pdf(post):
    print(maybe(f"Cleaning up pdf files for {post}"))
    shutil.rmtree(f"posts/{post}/temp/")
    if os.path.exists(f"posts/{post}/.auctex-auto/"):
        shutil.rmtree(f"posts/{post}/.auctex-auto/")
    print(good(f"Did clean up for {post} pdfs"))


def check_post(post):
    print(maybe(f"Checking that post {post} is ready to be generated"))
    if not os.path.isfile(f"posts/{post}/main.tex"):
        raise RuntimeError(warn(f"posts/{post}/main.tex does not exist, no post to build"))
    if not os.path.exists(f"posts/{post}/meta.json"):
        raise RuntimeError(warn(f"posts/{post}/meta.json does not exist, cannot get title"))

    print(maybe(f"Checks for post {post} were successful"))


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
        raise RuntimeError(warn(f"posts/{post}/temp/main.pdf was not built successfully"))

    # TODO: don't change directories
    os.chdir("../..")

    print(good(f"Successfully generated posts/{post}/temp/main.pdf"))


def clean_post(post):
    print(maybe(f"Cleaning up html files for {post}"))
    shutil.rmtree(f"posts/{post}/main/")
    os.remove(f"posts/{post}/{post}-templated.html")
    print(good(f"Did clean up for {post}"))


def gen_post(gen_dir, post):
    print(maybe(f"Building html for post {post}"))

    # Generate algo SVGs if they exist
    if os.path.exists(f"posts/{post}/algos"):
        gen_algos(gen_dir, post)

    # Render post fragment
    args = [
        "--extra-templates=template/commgrp",
        "--theme=commgrp",
        "--extra-css posts-commgroup.css",
        "--no-display-toc",
        "--split-level=-1",
        f"--dir=posts/{post}/main/",
        f"--image-filenames='{post}-images/$num'",
        f"--filename={post}",
    ]
    target = f"posts/{post}/main.tex"
    run_plastex(args, target)
    print(good(f"Built fragment for {post}"))

    with open(f"posts/{post}/meta.json", "r") as meta_data:
        meta = json.load(meta_data)

    # Assemble template
    input_html = f"posts/{post}/main/{post}.html"
    output_html = f"posts/{post}/{post}-templated.html"
    with open(input_html, "r") as content, open(output_html, "w") as curr_post:
        for line in content:
            # Fix style sheets as they live in one more directory above
            if 'rel="stylesheet"' in line:
                rep = line.replace("styles/", "../styles/")
                curr_post.write(rep)
            elif line[0:7] == "<title>":
                rep = f"<title>{meta["title"]}</title>"
                curr_post.write(rep)
            elif line == "<body>\n":
                curr_post.write(line)
                header = [
                    "<header>\n",
                    '<h1 id="doc_title"><a href="../index.html">commutative.group</a></h1>\n',
                    "</header>\n",
                    "\n",
                ]
                for head_line in header:
                    curr_post.write(head_line)
            elif line == "</body>\n":
                scripts = [
                    "\n",
                    '<script type="text/javascript" src="../js/jquery.min.js"></script>\n',
                    '<script type="text/javascript" src="../js/plastex.js"></script>\n',
                    '<script type="text/javascript" src="../js/svgxuse.js"></script>\n',
                ]
                for script_line in scripts:
                    curr_post.write(script_line)
                curr_post.write(line)
            else:
                curr_post.write(line)
        curr_post.write("\n")

    print(good(f"Wrote {post} to full file"))


def posts(gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(warn(f"{gen_dir}/ does not exist. Build main site first"))

    print(maybe("Building posts"))
    os.mkdir(f"{gen_dir}/posts/")
    # Each folder in posts/ is a post
    # The only required file is main.tex, the post
    # Any other tex files, as far as this function is concerned, do not exist

    # Copy posts-commgroup.css into main/posts/
    shutil.copy("posts-commgroup.css", f"{gen_dir}/styles/")
    print(good("Copied posts-commgroup.css"))

    # Render each post
    posts = next(os.walk("posts/"))[1]
    for post in posts:
        check_post(post)
        gen_post(gen_dir, post)
        gen_pdf(gen_dir, post)

        # Copy everything to gen_dir
        shutil.copy(f"posts/{post}/{post}-templated.html", f"{gen_dir}/posts/{post}.html")
        if os.path.exists(f"posts/{post}/main/{post}-images"):
            shutil.copytree(f"posts/{post}/main/{post}-images", f"{gen_dir}/posts/{post}-images")
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
    if not os.path.exists(f"{gen_dir}/styles/"):
        raise RuntimeError(warn(f"No styles/ folder in {gen_dir}"))
    else:
        pkg_css_files = ["amsthm"]
        for pkg_css in pkg_css_files:
            shutil.copy(f"template/packages/{pkg_css}.css", f"{gen_dir}/styles/{pkg_css}.css")
    if not os.path.exists(f"{gen_dir}/js/"):
        raise RuntimeError(warn(f"No js/ folder in {gen_dir}"))
    else:
        js = ["jquery.min", "plastex", "svgxuse"]
        for js_file in js:
            shutil.copy(f"template/commgrp/js/{js_file}.js", f"{gen_dir}/js/{js_file}.js")
    print(good("Copied template files"))

    print(good("Built Main Site"))


def fresh(gen_dir):
    if os.path.exists(gen_dir):
        print(maybe("Cleaning old generated directory"))

        html = [
            html_file[:-5]
            for html_file in next(os.walk(f"{gen_dir}"))[2]
            if html_file.endswith(".html")
        ]
        if len(html) > 0:
            print(maybe("Removing .html files"))
            for html_file in html:
                os.remove(f"{gen_dir}/{html_file}.html")

        if os.path.exists(f"{gen_dir}/js/"):
            print(maybe("Removing generated js/"))
            shutil.rmtree(f"{gen_dir}/js/")
        if os.path.exists(f"{gen_dir}/posts/"):
            print(maybe("Removing generated posts/"))
            shutil.rmtree(f"{gen_dir}/posts/")
        if os.path.exists(f"{gen_dir}/styles/"):
            print(maybe("Removing generated styles/"))
            shutil.rmtree(f"{gen_dir}/styles/")

        print(good("Cleaned old generated directory"))


def check_main(root_file):
    print(maybe("Checking for necessary files"))
    if not os.path.exists(f"{root_file}.tex"):
        raise RuntimeError(warn(f"Root file {root_file}.tex not found"))
    if not os.path.exists("posts/"):
        raise RuntimeError(warn("Posts folder posts not found"))
    if not os.path.exists("template/"):
        raise RuntimeError(warn("Templates folder templates/ not found"))
    else:
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
        else:
            if not os.path.exists("template/commgrp/js/"):
                raise RuntimeError(warn("commgrp/js/ does not exist in template/commgrp"))
            js = ["jquery.min", "plastex", "svgxuse"]
            print(maybe("Checking for the following .js files in template/commgrp/js:"))
            for js_file in js:
                print(f"    {js_file}.js")
            for js_file in js:
                if not os.path.exists(f"template/commgrp/js/{js_file}.js"):
                    raise RuntimeError(warn(f"{js_file}.js does not exist in template/commgrp/js/"))

        if not os.path.exists("template/algos/"):
            raise RuntimeError(warn("algos/ does not exist in template/"))
        stys = ["algo", "style", "ntabbing"]
        print(maybe("Checking for the following .sty files for algos:"))
        for sty in stys:
            print(f"    {sty}.sty")
        for sty in stys:
            if not os.path.exists(f"template/algos/{sty}.sty"):
                raise RuntimeError(warn(f"{sty}.sty does not exist in template/algos/"))

        if not os.path.exists("template/packages/"):
            raise RuntimeError(warn("packages/ does not exist in template/"))
        stylesheets = ["amsthm"]
        print(maybe("Checking for the following .css files in template/commgrp/packages:"))
        for css in stylesheets:
            print(f"    {css}.sty")
        for css in stylesheets:
            if not os.path.exists(f"template/packages/{css}.css"):
                raise RuntimeError(warn(f"{css}.css does not exist in template/packages/"))

    print(good("Found all necessary files"))


def main():
    root_file = "main"
    gen_dir = "gen"

    check_main(root_file)
    fresh(gen_dir)
    build_main(root_file, gen_dir)
    posts(gen_dir)
    clean_main(root_file, gen_dir)


if __name__ == "__main__":
    main()
