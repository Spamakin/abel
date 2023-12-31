#!/usr/local/bin/python3

import os
import shutil
import json


def run_plastex(args, target):
    print(f"[A] Running plasTeX with target {target} and the following args:")
    plastex_args = " "
    for arg in args:
        print(f"    {arg}")
        plastex_args += arg + " "
    cmd = "plastex" + plastex_args + f" -- {target}"
    os.system(cmd)


def posts(root_file, gen_dir):
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

        shutil.copy(f"posts/{post}/{post}-templated.html", f"{gen_dir}/posts/{post}.html")
        if os.path.exists(f"posts/{post}/main/{post}-images"):
            shutil.copytree(f"posts/{post}/main/{post}-images", f"{gen_dir}/posts/{post}-images")

        # Remove generated files for post
        print(f"[A] Cleaning up files for {post}")
        shutil.rmtree(f"posts/{post}/main")
        os.remove(f"posts/{post}/{post}-templated.html")

    print("[A] Built all posts")


def clean(root_file, gen_dir):
    if os.path.exists(f"{root_file}.paux"):
        os.remove(f"{root_file}.paux")
    if os.path.exists(gen_dir):
        shutil.rmtree(gen_dir)
    print("[A] Cleaned up files")


def fix_index(gen_dir):
    if not os.path.exists(f"{gen_dir}/"):
        raise RuntimeError(f"{gen_dir}/ does not exist. Build main site first")

    with open(f"{gen_dir}/index_fixed.html", "w") as idx_out:
        with open(f"{gen_dir}/index.html", "r") as idx_in:
            for line in idx_in:
                if "<title>" in line:
                    idx_out.write("<title>commutative.group</title>\n")
                else:
                    idx_out.write(line)
    os.remove(f"{gen_dir}/index.html")
    shutil.move(f"{gen_dir}/index_fixed.html", f"{gen_dir}/index.html")
    print("[A] Fixed title of index.html")

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

    fix_index(gen_dir)


def main():
    root_file = "main"
    gen_dir = "gen"

    # We assume we are working in the main directory
    if not os.path.exists(f"{root_file}.tex"):
        raise RuntimeError(f"{root_file}.tex does not exist in this location")

    clean(root_file, gen_dir)
    build_main(root_file, gen_dir)
    posts(root_file, gen_dir)


if __name__ == "__main__":
    main()
