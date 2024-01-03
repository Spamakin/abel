#!/usr/local/bin/python3

import os
import shutil
import json
import fitz


def run_plastex(args, target):
    print(f"[A] Running plasTeX with target {target} and the following args:")
    plastex_args = " "
    for arg in args:
        print(f"    {arg}")
        plastex_args += arg + " "
    cmd = "plastex" + plastex_args + f" -- {target}"
    os.system(cmd)


def gen_algos(gen_dir, post):
    if not os.path.exists(f"posts/{post}/algos"):
        raise RuntimeError(f"algos/ does not exist in posts/{post}, which is impossible.")

    # copy template/algos/style.sty, algo.sty, latexmkrc
    if not os.path.exists("template/algos"):
        raise RuntimeError("algos/ does not exist in template")
    else:
        stys = ["algo", "style", "ntabbing"]
        for sty in stys:
            if not os.path.exists(f"template/algos/{sty}.sty"):
                raise RuntimeError(f"{sty}.sty does not exist in template/algos")
            shutil.copy(f"template/algos/{sty}.sty", f"posts/{post}/algos/")
    print(f"[A] Building algorithm pngs for {post}")

    # for algo_name.tex in algos/
    # ends in .tex
    algos = [algo[:-4] for algo in next(os.walk(f"posts/{post}/algos"))[2] if algo.endswith(".tex")]
    print("[A] Building the following algorithm pngs:")
    for algo_name in algos:
        print(f"    {algo_name}")
    for algo_name in algos:
        # TODO: don't change directories
        os.chdir(f"posts/{post}/algos")

        print(f"[A] Building png for algorithm {post}/algos/{algo_name}.tex")

        # algo_name.tex -> algo_name.pdf
        # NOTE: --outdir is relative to -cd
        os.mkdir("temp")
        print(f"[A] Making temporary directory for algo {algo_name} generation")
        args = [
            "-pdf",
            # "-silent",
            "-outdir=temp/",
        ]
        latexmk_args = " "
        for arg in args:
            print(f"    {arg}")
            latexmk_args += arg + " "
        target = f"{algo_name}.tex"
        print(f"[A] Running Latexmk with target {target} and the following args:")
        cmd = "latexmk" + latexmk_args + target
        os.system(cmd)
        print(f"[A] Successfully generated temp/{algo_name}.pdf")

        # algo_name.pdf -> algo_name-crop.pdf
        cmd = f"pdfcrop temp/{algo_name}.pdf"
        os.system(cmd)
        print(f"[A] Cropped temp/{algo_name}.pdf")

        # algo_name-crop.pdf -> algo_name.png
        with fitz.open(f"temp/{algo_name}-crop.pdf") as cropped:
            for page in cropped:
                pix = page.get_pixmap(dpi=300)
                pix.save(f"{algo_name}.png")
        print(f"[A] Converted cropped pdf to {algo_name}.png")

        # TODO: don't change directories
        os.chdir("../../..")

        shutil.move(f"posts/{post}/algos/{algo_name}.png", f"posts/{post}/{algo_name}.png")
        print(f"[A] Moved {algo_name}.png to posts/{post}")

        shutil.rmtree(f"posts/{post}/algos/temp")
        # TODO: remove generated png?
        print(f"[A] Cleaned up generated files for algos/{algo_name}")

    stys = ["algo", "style", "ntabbing"]
    for sty in stys:
        os.remove(f"posts/{post}/algos/{sty}.sty")
    print(f"[A] Removed .sty files from posts/{post}")


def posts(gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(f"{gen_dir}/ does not exist. Build main site first")

    print("[A] Building posts")
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
    if not os.path.exists("template/posts-commgroup.css"):
        raise RuntimeError("posts-commgroup.css does not exist in template/")
    shutil.copy("template/posts-commgroup.css", f"{gen_dir}/styles/")
    print("[A] Copied posts-commgroup.css")

    if not os.path.exists("template/posts-start.html"):
        raise RuntimeError("posts-start.html does not exist in template/")
    if not os.path.exists("template/posts-end.html"):
        raise RuntimeError("posts-end.html does not exist in template/")
    print("[A] Found template start and end")

    # Render each post
    posts = next(os.walk("posts/"))[1]
    for post in posts:
        print(f"[A] Building post {post}")
        if not os.path.isfile(f"posts/{post}/main.tex"):
            raise RuntimeError(f"posts/{post}/main.tex does not exist, no post to build")

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
        print(f"[A] Built fragment for {post}")

        if not os.path.exists(f"posts/{post}/meta.json"):
            raise RuntimeError(f"posts/{post}/meta.json does not exist, cannot get title")
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

        print(f"[A] Wrote {post} to full file")

        # TODO: PDFs

        # Copy everything to gen_dir
        shutil.copy(f"posts/{post}/{post}-templated.html", f"{gen_dir}/posts/{post}.html")
        if os.path.exists(f"posts/{post}/main/{post}-images"):
            shutil.copytree(f"posts/{post}/main/{post}-images", f"{gen_dir}/posts/{post}-images")

        # Remove generated files for post
        print(f"[A] Cleaning up files for {post}")
        shutil.rmtree(f"posts/{post}/main/")
        # TODO: sometimes .auxtex-auto exists and sometimes it doesn't
        if os.path.exists(f"posts/{post}/.auctex-auto/"):
            shutil.rmtree(f"posts/{post}/.auctex-auto/")
        os.remove(f"posts/{post}/{post}-templated.html")
        print(f"[A] Did clean up for {post}")

    print("[A] Built all posts")


def clean(root_file, gen_dir):
    if os.path.exists(f"{root_file}.paux"):
        os.remove(f"{root_file}.paux")
    if os.path.exists(gen_dir):
        shutil.rmtree(gen_dir)
    if os.path.exists(f".auctex-auto/"):
        shutil.rmtree(f".auctex-auto/")
    print("[A] Cleaned up files")


def fix_title_front(gen_dir, target_file, title):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(f"{gen_dir}/ does not exist. Build main site first")

    with open(f"{gen_dir}/{target_file}_fixed.html", "w") as idx_out:
        with open(f"{gen_dir}/{target_file}.html", "r") as idx_in:
            for line in idx_in:
                if "<title>" in line:
                    idx_out.write(f"<title>{title}</title>\n")
                else:
                    idx_out.write(line)
    os.remove(f"{gen_dir}/{target_file}.html")
    shutil.move(f"{gen_dir}/{target_file}_fixed.html", f"{gen_dir}/{target_file}.html")
    print(f"[A] Fixed title of {target_file}.html")


def clean_main(gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(f"{gen_dir}/ does not exist. Build main site first")

    # remove unused CSS
    os.remove(f"{gen_dir}/styles/green.css")
    os.remove(f"{gen_dir}/styles/white.css")
    os.remove(f"{gen_dir}/styles/blue.css")
    print("[A] Removed unused CSS generated by plasTeX")


def build_main(root_file, gen_dir):
    print("[A] Building main files")

    args = [
        "--extra-css theme-commgroup.css",
        "--no-theme-css",
        "--no-display-toc",
        "--filename='index [$title]'",
        "--split-level=-1",
        f"--dir={gen_dir}",
    ]
    target = f"{root_file}.tex"
    run_plastex(args, target)

    print("[A] Built Main Site")

    fix_title_front(gen_dir, "index", "commutative.group")
    fix_title_front(gen_dir, "About", "About")
    fix_title_front(gen_dir, "All-Posts", "All Posts")


def main():
    root_file = "main"
    gen_dir = "gen"

    # We assume we are working in the main directory
    if not os.path.exists(f"{root_file}.tex"):
        raise RuntimeError(f"{root_file}.tex does not exist in this location")

    clean(root_file, gen_dir)
    build_main(root_file, gen_dir)
    posts(gen_dir)


if __name__ == "__main__":
    main()
