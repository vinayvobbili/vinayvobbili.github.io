#!/usr/bin/env ruby
#
# The hero image at the top of a post is the largest thing above the fold, but Chirpy's
# refactor-content include marks every <img> loading="lazy". Make that one eager and
# high priority so it can paint first; images further down the post stay lazy.

HERO_IMG = /(<a [^>]*class="[^"]*preview-img[^"]*"[^>]*>\s*<img [^>]*?)\s+loading="lazy"/

Jekyll::Hooks.register :posts, :post_render do |post|
  post.output = post.output.sub(HERO_IMG, '\1 fetchpriority="high"')
end
