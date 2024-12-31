import json
import os
# from llm.model import groq_mixtral_model
from llm.model import gemini_generative_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import chain
from fuzzywuzzy import fuzz
import re
from llm.prompts.sql_prompt import sql_prompt
from llm.schema.sql_query import SqlQuery
from utils.execute_query import execute_query

# Define the structured model for generating SQL queries
# structured_model = gemini_generative_model.with_structured_output(SqlQuery)

def get_dynamic_user_order_response() -> str:
  system_instructions = """
  INSTRUCTIONS:
    - You are to generate human language response in string format based on user queries and response coming for sql query in a single sentence.
    - Response should start with greetings.
    - {order_id} is order number and {product_id} is product id.
    - Response should be in context with user query.
    - Nno need to show quantity.
    - If user query related to order status then show {order_id} followed by # symbol.
    
  """
  return system_instructions

def get_dynamic_user_product_response() -> str:
  system_instructions = """
  INSTRUCTIONS:
    - You are to generate human language response in string format based on user queries and response coming for sql query in a single sentence.
    - Response must be similar to below examples and select the examples randomly:
    Examples: 
    "Indeed, we have a {title}. Please follow the link to show the product."
    "Yes, we have a {title}. Would that work?"
    "We do have a {title} available. Would that be suitable for your needs?"
    - Response should be in context with user query.
    
  """
  return system_instructions

def get_dynamic_user_price_response() -> str:
  system_instructions = """
  INSTRUCTIONS:
    - You are to generate human language response in string format based on user queries and response coming for sql query in a single sentence.
    - Response should start by thanking the user and should be random.
    - Response should be in context with user query.
    - If user query related to product price then need to show {title} of the product includes({product_id}).
    - {price_chart} is the starting price for the {quantity} and response should includes this.
    
  """
  return system_instructions


def get_dynamic_sql_prompt_product() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default",
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: product_images
      CREATE TABLE IF NOT EXISTS public.product_images
      (
          product_id integer NOT NULL,
          image_id character varying COLLATE pg_catalog."default" NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          type integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_10de97980da2e939c4c0e8423f2" PRIMARY KEY (product_id, image_id),
          CONSTRAINT "FK_2212515ba306c79f42c46a99db7" FOREIGN KEY (image_id)
              REFERENCES public.image (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE CASCADE,
          CONSTRAINT fk_4f166bb8c2bfcef2498d97b4068 FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE NO ACTION
      )
    
    Table: image
      CREATE TABLE IF NOT EXISTS public.image
      (
          id character varying COLLATE pg_catalog."default" NOT NULL,
          url character varying COLLATE pg_catalog."default" NOT NULL,
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_d6db1ab4ee9ad9dbe86c64e4cc3" PRIMARY KEY (id)
      )

    INSTRUCTIONS:
    - You are to generate SQL queries based on dynamic user queries.
    - User may ask to filter products based on column values.
    - Support numeric comparisons such as 'greater than', 'less than', 'equal to', etc., for columns like weight, length, height, width.
    - For text fields like title, etc., use 'ILIKE' for case-insensitive searches and partial matches.
    - If user query includes any type like, custom, two tone, rush, nylon, woven then the title of the should include this.
    - If user query exist about product in plural or singular form like lanyard or lanyards then create sql accordingly to match the `p.title` both singular and plural.
    - If the user asks for multiple conditions (e.g., weight > 10 AND height < 50), ensure to include both conditions in the query.
    - Always use the LEFT JOIN on the `product_images` table to retrieve associated images.

    EXAMPLES:
    1. User Query: "Show me products with a weight greater than 10."
       Generated SQL:
       SELECT p.*, i.url
       FROM product p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.weight > 10;

    2. User Query: "Find products with height less than 50 and width greater than 20."
       Generated SQL:
       SELECT p.*, i.url
       FROM product p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.height < 50 AND p.width > 20;

    3. User Query: "I need products made from nylon."
       Generated SQL:
       SELECT p.*, i.url
       FROM product p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.title ILIKE '%nylon%' 
       AND p.title ILIKE ANY (ARRAY['%lanyard%', '%lanyards%']);

    4. User Query: "List products with title similar to 'Lanyard'."
       Generated SQL:
       SELECT p.*, i.url
       FROM product p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.title ILIKE ANY (ARRAY['%lanyard%', '%lanyards%']);

    5. User Query: "Find products with a width greater than 30 and made in the USA."
       Generated SQL:
       SELECT p.*, i.url
       FROM product p
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.width > 30 AND p.origin_country ILIKE '%USA%';

    - Ensure that numeric comparisons are properly handled using the operators '>', '<', '>=', '<=', and '=' as per the user's input.
    - For string-based searches (e.g., title, origin_country), always use the ILIKE operator for case-insensitive matching.
    """
    return system_instructions



# Create the dynamic SQL prompt function
def get_dynamic_sql_prompt_order() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: lanyard_order
      CREATE TABLE public.lanyard_order
        (
            id integer NOT NULL DEFAULT nextval('lanyard_order_id_seq'::regclass),
            customer_id character varying COLLATE pg_catalog."default" NOT NULL,
            cart_id integer NOT NULL,
            total_price numeric(10,2) NOT NULL DEFAULT 0,
            status character varying COLLATE pg_catalog."default" NOT NULL,
            created_at timestamp without time zone NOT NULL DEFAULT now(),
            updated_at timestamp without time zone NOT NULL DEFAULT now(),
            date timestamp without time zone,
            price numeric(10,2) DEFAULT 0,
            shipping_address_id character varying COLLATE pg_catalog."default",
            CONSTRAINT "PK_5d45c09313f20df64f5f71426df" PRIMARY KEY (id),
            CONSTRAINT "FK_b3f5fcf97dfe91a2af47a8334fc" FOREIGN KEY (shipping_address_id)
                REFERENCES public.address (id) MATCH SIMPLE
                ON UPDATE CASCADE
                ON DELETE SET NULL,
            CONSTRAINT "FK_d590b85850406678d5885bbddfe" FOREIGN KEY (customer_id)
                REFERENCES public.customer (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE RESTRICT,
            CONSTRAINT "FK_e046d5806268da2a40ffc883f8b" FOREIGN KEY (cart_id)
                REFERENCES public.lanyard_cart (id) MATCH SIMPLE
                ON UPDATE NO ACTION
                ON DELETE RESTRICT
        )

    Table: lanyard_order_items
      CREATE TABLE public.lanyard_order_items
      (
          id integer NOT NULL DEFAULT nextval('lanyard_order_items_id_seq'::regclass),
          order_id integer NOT NULL,
          product_id integer NOT NULL,
          price numeric(10,2) NOT NULL DEFAULT 0,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          extra_charge character varying COLLATE pg_catalog."default",
          delivery_date timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_cbcd5341319f5294a7e28c6a7bb" PRIMARY KEY (id),
          CONSTRAINT "FK_6265cd7e252c426649a0e7c5d34" FOREIGN KEY (order_id)
              REFERENCES public.lanyard_order (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_f7681aab54945922928684dff68" FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: order_color
      CREATE TABLE public.order_color
      (
          id integer NOT NULL DEFAULT nextval('order_color_id_seq'::regclass),
          order_item_id integer NOT NULL,
          color_id integer NOT NULL,
          quantity integer NOT NULL,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_9c5ffa02296894dcace50b2dc7a" PRIMARY KEY (id),
          CONSTRAINT "FK_49c8c19f72165df2f38007123d7" FOREIGN KEY (order_item_id)
              REFERENCES public.lanyard_order_items (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_fdf13288bed721b1487b0619786" FOREIGN KEY (color_id)
              REFERENCES public.color (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: order_size
      CREATE TABLE IF NOT EXISTS public.order_size
      (
          id integer NOT NULL DEFAULT nextval('order_size_id_seq'::regclass),
          order_item_id integer NOT NULL,
          size_id integer NOT NULL,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_cc492be4c64abae244c4f318a00" PRIMARY KEY (id),
          CONSTRAINT "FK_aa12341229a8f0216356ce87518" FOREIGN KEY (order_item_id)
              REFERENCES public.lanyard_order_items (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_b14e08de126c71d594192d4410a" FOREIGN KEY (size_id)
              REFERENCES public.size (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: color
      CREATE TABLE IF NOT EXISTS public.color
      (
          id integer NOT NULL DEFAULT nextval('color_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default" NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          code character varying COLLATE pg_catalog."default" NOT NULL,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          category_id integer NOT NULL,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_d15e531d60a550fbf23e1832343" PRIMARY KEY (id),
          CONSTRAINT "FK_3707801ea0041ee2f3bdc180fbc" FOREIGN KEY (category_id)
              REFERENCES public.color_category (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: size
      CREATE TABLE IF NOT EXISTS public.size
      (
          id integer NOT NULL DEFAULT nextval('size_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default",
          mm double precision,
          inch double precision,
          size_type character varying COLLATE pg_catalog."default",
          deleted integer NOT NULL DEFAULT 0,
          category_id integer NOT NULL DEFAULT 1,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          measurement integer,
          extra_charge numeric(10,2) DEFAULT 0,
          CONSTRAINT "PK_66e3a0111d969aa0e5f73855c7a" PRIMARY KEY (id),
          CONSTRAINT "FK_1e976d825e6681db9090d24fbbc" FOREIGN KEY (category_id)
              REFERENCES public.size_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: image
      CREATE TABLE IF NOT EXISTS public.image
      (
          id character varying COLLATE pg_catalog."default" NOT NULL,
          url character varying COLLATE pg_catalog."default" NOT NULL,
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_d6db1ab4ee9ad9dbe86c64e4cc3" PRIMARY KEY (id)
      )

    INSTRUCTIONS:
    - You are to generate SQL queries dynamically based on user input for order-related queries.
    - For each query, first retrieve data from the `lanyard_order` table and join it with `lanyard_order_items` using the `order_id`.
    - Use the `order_color` table to retrieve color details by joining it with `color` based on `color_id`.
    - Similarly, use the `order_size` table to retrieve size details and link them with `size`.
    - Also join the `product` table to retrieve product information and link `product_images` to fetch product images.
    - Always use 'LEFT JOIN' to ensure all items are retrieved, even if some fields like color, size, or product images are missing.
    - Use filters like `customer_id` to retrieve customer-specific orders and sort by `created_at` to retrieve the most recent order if requested.
    - If the user asks for "last order," prioritize retrieving the most recent order based on the `created_at` or `updated_at`.
    - If user ask for price for their order then first retrieve all column data from the `lanyard_order` table and join it with `lanyard_order_items` using the `order_id`. Also retreive data from product table and left join
    - If user ask for status of their order then first retrieve all column data from the `lanyard_order` table and join it with `lanyard_order_items` using the `order_id`. Also retreive all data from product table and left join

    EXAMPLES:

    1. User Query: "What is my last order?"
       Generated SQL:
       SELECT o.*, i.product_id, c.color_id, col.name AS color_name, s.size_id, sz.name AS size_name, p.material, p.title, total_price, img.url AS product_image_url
       FROM lanyard_order o
       LEFT JOIN lanyard_order_items i ON o.id = i.order_id
       LEFT JOIN order_color c ON i.id = c.order_item_id
       LEFT JOIN color col ON c.color_id = col.id
       LEFT JOIN order_size s ON i.id = s.order_item_id
       LEFT JOIN size sz ON s.size_id = sz.id
       LEFT JOIN product p ON i.product_id = p.id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image img ON pi.image_id = img.id
       WHERE o.customer_id = '{customer_id}'
       ORDER BY o.created_at DESC
       LIMIT 1;

    2. User Query: "Show me orders from last week."
       Generated SQL:
       SELECT o.*, i.product_id, c.color_id, col.name AS color_name, s.size_id, sz.name AS size_name, p.material, p.title, total_price, img.url AS product_image_url
       FROM lanyard_order o
       LEFT JOIN lanyard_order_items i ON o.id = i.order_id
       LEFT JOIN order_color c ON i.id = c.order_item_id
       LEFT JOIN color col ON c.color_id = col.id
       LEFT JOIN order_size s ON i.id = s.order_item_id
       LEFT JOIN size sz ON s.size_id = sz.id
       LEFT JOIN product p ON i.product_id = p.id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image img ON pi.image_id = img.id
       WHERE o.customer_id = '{customer_id}'
       AND o.created_at >= NOW() - INTERVAL '7 days'
       ORDER BY o.created_at DESC;

    3. User Query: "Show me the details of my order with number 123456."
       Generated SQL:
       SELECT o.*, i.product_id, c.color_id, col.name AS color_name, s.size_id, sz.name AS size_name, p.material, p.title, total_price, img.url AS product_image_url
       FROM lanyard_order o
       LEFT JOIN lanyard_order_items i ON o.id = i.order_id
       LEFT JOIN order_color c ON i.id = c.order_item_id
       LEFT JOIN color col ON c.color_id = col.id
       LEFT JOIN order_size s ON i.id = s.order_item_id
       LEFT JOIN size sz ON s.size_id = sz.id
       LEFT JOIN product p ON i.product_id = p.id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image img ON pi.image_id = img.id
       WHERE o.customer_id = '{customer_id}' AND o.id = '123456';

    - For queries about the "last order" or orders within a specific timeframe, always sort by `created_at` or `updated_at` in descending order.
    - For queries about the "first order", always sort by `created_at` or `updated_at` in ascending order.
    - If the user asks for orders by number, use the order `id` or relevant identifier to filter the query.
    - For any missing fields, ensure the query still returns meaningful results using `LEFT JOIN`.
    """
    return system_instructions


def get_dynamic_sql_prompt_price() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default", -- ignore this column
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: product_price_chart
      CREATE TABLE IF NOT EXISTS public.product_price_chart
      (
          id integer NOT NULL DEFAULT nextval('product_price_chart_id_seq'::regclass),
          product_id integer NOT NULL,
          size_id integer NOT NULL,
          attachment_style_id integer NOT NULL,
          price_chart jsonb NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_3b306976fff3e58acf6dc2cd161" PRIMARY KEY (id),
          CONSTRAINT "FK_8769953d1868308af72e3b19994" FOREIGN KEY (attachment_style_id)
              REFERENCES public.attachment_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_99ae9d2a58851d6e5a82471f298" FOREIGN KEY (size_id)
              REFERENCES public.size (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_c8a360a6bd9c45149d0c1297cee" FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: product_images
      CREATE TABLE IF NOT EXISTS public.product_images
      (
          product_id integer NOT NULL,
          image_id character varying COLLATE pg_catalog."default" NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          type integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_10de97980da2e939c4c0e8423f2" PRIMARY KEY (product_id, image_id),
          CONSTRAINT "FK_2212515ba306c79f42c46a99db7" FOREIGN KEY (image_id)
              REFERENCES public.image (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE CASCADE,
          CONSTRAINT fk_4f166bb8c2bfcef2498d97b4068 FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE NO ACTION
      )

    Table: image
      CREATE TABLE IF NOT EXISTS public.product_images
      (
          product_id integer NOT NULL,
          image_id character varying COLLATE pg_catalog."default" NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          type integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_10de97980da2e939c4c0e8423f2" PRIMARY KEY (product_id, image_id),
          CONSTRAINT "FK_2212515ba306c79f42c46a99db7" FOREIGN KEY (image_id)
              REFERENCES public.image (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE CASCADE,
          CONSTRAINT fk_4f166bb8c2bfcef2498d97b4068 FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE NO ACTION
      )

    Table: attachment_styles
      CREATE TABLE IF NOT EXISTS public.attachment_styles
      (
          id integer NOT NULL DEFAULT nextval('attachment_styles_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          colors character varying(255) COLLATE pg_catalog."default",
          product_image text COLLATE pg_catalog."default",
          category_id integer,
          selected_attachment integer,
          deleted integer NOT NULL DEFAULT 0,
          is_premium boolean,
          extra_charge numeric(10,2) DEFAULT 0,
          premium_clip integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_ec11d3083091459a072972a5ebc" PRIMARY KEY (id),
          CONSTRAINT fk_category FOREIGN KEY (category_id)
              REFERENCES public.attachment_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    INSTRUCTIONS:
    - You are to generate SQL queries based on user queries regarding product prices and images.
    - Extract the product name from the user query to find the corresponding product ID in the product table.
    - If the user specifies additional criteria such as size, width, or attachment style, extract those details from the user query.
    - If all specific criteria (size, width, attachment style, product_id) are provided, generate an SQL query to find the exact match.
    - If no specific criteria are provided, return all relevant price options and images for the product.
    - Retrieve price information from the product_price_chart based on the found product ID, along with any specified `size_id`, `width`, and `attachment_style_id`.
    - Retrieve images from the product_images table, joining with the image table to get the image `url` using `image_id`.
    - If user query exist about product in plural or singular form like lanyard or lanyards then create sql accordingly to match the `p.title` both singular and plural.
    - When querying for attachment styles, join the `attachment_styles` table using `attachment_style_id` to filter results based on the specified attachment style.
    - Always return the relevant product information, including its images and attachment styles, alongside its price.

    EXAMPLES:
    1. User Query: "What is the price of the lanyard?"
       Generated SQL:
       SELECT p.*, pp.price_chart, i.url
       FROM product p
       LEFT JOIN product_price_chart pp ON p.id = pp.product_id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.title ILIKE '%lanyard%';

    2. User Query: "Show me the price for the red lanyard in size medium."
       Generated SQL:
       SELECT p.*, pp.price_chart, i.url
       FROM product p
       LEFT JOIN product_price_chart pp ON p.id = pp.product_id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.title ILIKE '%red%'
       AND p.title ILIKE ANY (ARRAY['%lanyard%', '%lanyards%']);
       AND pp.size_id = (SELECT id FROM size WHERE title ILIKE '%medium%');

    3. User Query: "What is the price of the lanyard with attachment style A?"
       Generated SQL:
       SELECT p.*, pp.price_chart, i.url
       FROM product p
       LEFT JOIN product_price_chart pp ON p.id = pp.product_id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       LEFT JOIN attachment_styles a ON pp.attachment_style_id = a.id
       WHERE p.title ILIKE '%lanyard%'
       AND a.name ILIKE '%A%';

    4. User Query: "Find me the lanyard with width 5 and attachment style B."
       Generated SQL:
       SELECT p.*, pp.price_chart, i.url
       FROM product p
       LEFT JOIN product_price_chart pp ON p.id = pp.product_id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       LEFT JOIN attachment_styles a ON pp.attachment_style_id = a.id
       WHERE p.title ILIKE '%lanyard%'
       AND a.name ILIKE '%B%'
       AND p.width = 5;

    5. User Query: "What are the prices and images for lanyards?"
       Generated SQL:
       SELECT p.*, pp.price_chart, i.url
       FROM product p
       LEFT JOIN product_price_chart pp ON p.id = pp.product_id
       LEFT JOIN product_images pi ON p.id = pi.product_id
       LEFT JOIN image i ON pi.image_id = i.id
       WHERE p.title ILIKE '%lanyard%';
    """
    return system_instructions



def get_dynamic_sql_prompt_for_price_with_attachment_new() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: size
      CREATE TABLE IF NOT EXISTS public.size
      (
          id integer NOT NULL DEFAULT nextval('size_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default",
          mm double precision,
          inch double precision,
          size_type character varying COLLATE pg_catalog."default",
          deleted integer NOT NULL DEFAULT 0,
          category_id integer NOT NULL DEFAULT 1,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          measurement integer,
          extra_charge numeric(10,2) DEFAULT 0,
          CONSTRAINT "PK_66e3a0111d969aa0e5f73855c7a" PRIMARY KEY (id),
          CONSTRAINT "FK_1e976d825e6681db9090d24fbbc" FOREIGN KEY (category_id)
              REFERENCES public.size_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default",
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: attachment_categories
      CREATE TABLE IF NOT EXISTS public.attachment_categories
      (
          id integer NOT NULL DEFAULT nextval('attachment_categories_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          info_image text COLLATE pg_catalog."default",
          label character varying(255) COLLATE pg_catalog."default",
          active_attachment integer NOT NULL DEFAULT 0,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_49b0da9551096c6fd9fd69ace5f" PRIMARY KEY (id)
      )

    INSTRUCTIONS:
    - You are to generate SQL queries based on user inputs specifically for retrieving the product ID, size ID, attachment category ID, and price.
    - Accept the following inputs from the user: product name, size name (e.g., width), size measurement, and attachment style.
    - When looking for a size, retrieve the `id` from the `size` table based on both the specified `name` and `measurement`.
    - Extract the product name and attachment style from the user query to find the corresponding `id` in the `product` and `attachment_categories` tables.
    - Generate the SQL queries to fetch the price information based on the retrieved IDs.

    EXAMPLES:
    1. User Query: "Give me price for product name pone with width 1 having attachment style of single clip."
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, pp.price_chart 
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 1 AND s.deleted = 0 
       JOIN attachment_categories a ON a.name ILIKE '%single clip%' 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       WHERE p.title ILIKE '%pone%';

    2. User Query: "What is the price for the backpack with width 30 and attachment style double clip?"
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, pp.price_chart 
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 30 AND s.deleted = 0 
       JOIN attachment_categories a ON a.name ILIKE '%double clip%' 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       WHERE p.title ILIKE '%backpack%';

    3. User Query: "Find me the price for product A with width of 5 and attachment style clip."
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, pp.price_chart 
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 5 AND s.deleted = 0 
       JOIN attachment_categories a ON a.name ILIKE '%clip%' 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       WHERE p.title ILIKE '%product A%';

    4. User Query: "What is the price for the item with width 15 and attachment style none?"
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, pp.price_chart 
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 15 AND s.deleted = 0 
       JOIN attachment_categories a ON a.name ILIKE '%none%' 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       WHERE p.title ILIKE '%item%';

    5. User Query: "Show me the price for my product X with width 10 and attachment style custom."
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, pp.price_chart 
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 10 AND s.deleted = 0 
       JOIN attachment_categories a ON a.name ILIKE '%custom%' 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       WHERE p.title ILIKE '%product X%';
    """
    return system_instructions




def get_dynamic_sql_prompt_for_price_with_attachment_new() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: size
      CREATE TABLE IF NOT EXISTS public.size
      (
          id integer NOT NULL DEFAULT nextval('size_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default",
          mm double precision,
          inch double precision,
          size_type character varying COLLATE pg_catalog."default",
          deleted integer NOT NULL DEFAULT 0,
          category_id integer NOT NULL DEFAULT 1,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          measurement integer,
          extra_charge numeric(10,2) DEFAULT 0,
          CONSTRAINT "PK_66e3a0111d969aa0e5f73855c7a" PRIMARY KEY (id),
          CONSTRAINT "FK_1e976d825e6681db9090d24fbbc" FOREIGN KEY (category_id)
              REFERENCES public.size_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default",
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: attachment_categories
      CREATE TABLE IF NOT EXISTS public.attachment_categories
      (
          id integer NOT NULL DEFAULT nextval('attachment_categories_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          info_image text COLLATE pg_catalog."default",
          label character varying(255) COLLATE pg_catalog."default",
          active_attachment integer NOT NULL DEFAULT 0,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_49b0da9551096c6fd9fd69ace5f" PRIMARY KEY (id)
      )

    INSTRUCTIONS:
    - You are to generate SQL queries based on user inputs specifically for retrieving the product ID, size ID, attachment category ID, and price.
    - Accept the following inputs from the user: product name, size name (e.g., width), size measurement, attachment style, and quantity.
    - Ensure that the attachment style is converted to lower case and spaces are replaced with underscores for the comparison.
    - If only the product name is provided, return the first matching product.
    - If size name and measurement are provided, retrieve the `id` from the `size` table based on the specified `name` and `measurement`.
    - Generate the SQL queries to fetch the price information based on the retrieved IDs, prioritizing available criteria.

    EXAMPLES:
    1. User Query: "Give me price for product name pone with width 1 having attachment style of single clip."
       Generated SQL:
       SELECT p.id AS product_id, 
              s.id AS size_id, 
              a.id AS attachment_id, 
              q->>'price' AS price  
       FROM product p  
       JOIN size s ON s.name ILIKE '%width%' 
                    AND s.measurement = 1 
                    AND s.deleted = 0  
       JOIN attachment_categories a ON LOWER(REPLACE(a.name, ' ', '_')) = LOWER(REPLACE('single clip', ' ', '_'))  
       JOIN product_price_chart pp ON pp.product_id = p.id 
                                   AND pp.size_id = s.id 
                                   AND pp.attachment_style_id = a.id  
       CROSS JOIN LATERAL jsonb_array_elements(pp.price_chart) AS q  
       WHERE p.title ILIKE '%pone%' 
         AND (q->>'quantity')::int <= 20  
       LIMIT 1;

    2. User Query: "What is the price for the backpack with width 30 and attachment style double clip?"
       Generated SQL:
       SELECT p.id AS product_id, 
              s.id AS size_id, 
              a.id AS attachment_id, 
              q->>'price' AS price  
       FROM product p  
       JOIN size s ON s.name ILIKE '%width%' 
                    AND s.measurement = 30 
                    AND s.deleted = 0  
       JOIN attachment_categories a ON LOWER(REPLACE(a.name, ' ', '_')) = LOWER(REPLACE('double clip', ' ', '_'))  
       JOIN product_price_chart pp ON pp.product_id = p.id 
                                   AND pp.size_id = s.id 
                                   AND pp.attachment_style_id = a.id  
       CROSS JOIN LATERAL jsonb_array_elements(pp.price_chart) AS q  
       WHERE p.title ILIKE '%backpack%' 
         AND (q->>'quantity')::int <= 20  
       LIMIT 1;
    """
    return system_instructions


def get_dynamic_sql_prompt_for_price_with_nearest_quantity_altered() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: size
      CREATE TABLE IF NOT EXISTS public.size
      (
          id integer NOT NULL DEFAULT nextval('size_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default",
          mm double precision,
          inch double precision,
          size_type character varying COLLATE pg_catalog."default",
          deleted integer NOT NULL DEFAULT 0,
          category_id integer NOT NULL DEFAULT 1,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          measurement integer,
          extra_charge numeric(10,2) DEFAULT 0,
          CONSTRAINT "PK_66e3a0111d969aa0e5f73855c7a" PRIMARY KEY (id),
          CONSTRAINT "FK_1e976d825e6681db9090d24fbbc" FOREIGN KEY (category_id)
              REFERENCES public.size_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default",
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: attachment_categories
      CREATE TABLE IF NOT EXISTS public.attachment_categories
      (
          id integer NOT NULL DEFAULT nextval('attachment_categories_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          info_image text COLLATE pg_catalog."default",
          label character varying(255) COLLATE pg_catalog."default",
          active_attachment integer NOT NULL DEFAULT 0,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_49b0da9551096c6fd9fd69ace5f" PRIMARY KEY (id)
      )

    INSTRUCTIONS:
    - Generate SQL queries based on user inputs specifically for retrieving the product ID, size ID, attachment category ID, and price.
    - Accept the following inputs from the user: product name, size name (e.g., width), size measurement, attachment style, and quantity.
    - Convert the attachment style to lower case and replace spaces with underscores before comparison.
    - If a quantity is provided, retrieve the nearest item based on quantity instead of using a "less than or equal to" condition.
    - Extract the product name and attachment style from the user query to find the corresponding IDs in the product and attachment_categories tables.
    - Generate the SQL queries to fetch the price information based on the retrieved IDs, prioritizing available criteria.

    EXAMPLES:
    1. User Query: "Give me price for product name pone with width 1 having attachment style of single clip and quantity 10."
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, q->>'price' AS price
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 1 AND s.deleted = 0 
       JOIN attachment_categories a ON LOWER(REPLACE(a.name, ' ', '_')) = LOWER(REPLACE('single clip', ' ', '_')) 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       CROSS JOIN LATERAL jsonb_array_elements(pp.price_chart) AS q 
       WHERE p.title ILIKE '%pone%' 
       ORDER BY ABS((q->>'quantity')::int - 10) 
       LIMIT 1;

    2. User Query: "What is the price for the backpack with width 30 and attachment style double clip with quantity 15?"
       Generated SQL:
       SELECT p.id AS product_id, s.id AS size_id, a.id AS attachment_id, q->>'price' AS price
       FROM product p 
       JOIN size s ON s.name ILIKE '%width%' AND s.measurement = 30 AND s.deleted = 0 
       JOIN attachment_categories a ON LOWER(REPLACE(a.name, ' ', '_')) = LOWER(REPLACE('double clip', ' ', '_')) 
       JOIN product_price_chart pp ON pp.product_id = p.id AND pp.size_id = s.id AND pp.attachment_style_id = a.id 
       CROSS JOIN LATERAL jsonb_array_elements(pp.price_chart) AS q 
       WHERE p.title ILIKE '%backpack%' 
       ORDER BY ABS((q->>'quantity')::int - 15) 
       LIMIT 1;
    """
    return system_instructions



def get_dynamic_sql_prompt_for_price_chart() -> str:
    system_instructions = """
    Act as a PostgreSQL query generator with access to the following database schema:

    Table: size
      CREATE TABLE IF NOT EXISTS public.size
      (
          id integer NOT NULL DEFAULT nextval('size_id_seq'::regclass),
          image character varying COLLATE pg_catalog."default",
          mm double precision,
          inch double precision,
          size_type character varying COLLATE pg_catalog."default",
          deleted integer NOT NULL DEFAULT 0,
          category_id integer NOT NULL DEFAULT 1,
          name character varying COLLATE pg_catalog."default" NOT NULL,
          measurement integer,
          extra_charge numeric(10,2) DEFAULT 0,
          CONSTRAINT "PK_66e3a0111d969aa0e5f73855c7a" PRIMARY KEY (id),
          CONSTRAINT "FK_1e976d825e6681db9090d24fbbc" FOREIGN KEY (category_id)
              REFERENCES public.size_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: product
      CREATE TABLE IF NOT EXISTS public.product
      (
          id integer NOT NULL DEFAULT nextval('product_id_seq'::regclass),
          title character varying COLLATE pg_catalog."default" NOT NULL,
          subtitle character varying COLLATE pg_catalog."default",
          description character varying COLLATE pg_catalog."default",
          handle character varying COLLATE pg_catalog."default",
          is_giftcard boolean NOT NULL DEFAULT false,
          thumbnail character varying COLLATE pg_catalog."default",
          weight integer,
          length integer,
          height integer,
          width integer,
          hs_code character varying COLLATE pg_catalog."default",
          origin_country character varying COLLATE pg_catalog."default",
          mid_code character varying COLLATE pg_catalog."default",
          material character varying COLLATE pg_catalog."default",
          created_at timestamp with time zone NOT NULL DEFAULT now(),
          updated_at timestamp with time zone NOT NULL DEFAULT now(),
          deleted_at timestamp with time zone,
          metadata jsonb,
          collection_id character varying COLLATE pg_catalog."default",
          type_id character varying COLLATE pg_catalog."default",
          discountable boolean NOT NULL DEFAULT true,
          status product_status_enum NOT NULL DEFAULT 'draft'::product_status_enum, -- status would draft or published
          external_id character varying COLLATE pg_catalog."default",
          msg_basic_form boolean DEFAULT false,
          stitch_style boolean DEFAULT false,
          lanyard_upgrades boolean DEFAULT false,
          badge_reel_keychain boolean DEFAULT false,
          badge_holder_options boolean DEFAULT false,
          imprint_option boolean DEFAULT false,
          attachment_style boolean DEFAULT false,
          msg_imprint_option boolean DEFAULT false,
          msg_imprint_no_colors boolean DEFAULT false,
          deleted integer NOT NULL DEFAULT 0,
          price numeric(10,2) NOT NULL DEFAULT 0,
          CONSTRAINT product_id_pkey PRIMARY KEY (id)
      )

    Table: attachment_categories
      CREATE TABLE IF NOT EXISTS public.attachment_categories
      (
          id integer NOT NULL DEFAULT nextval('attachment_categories_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          info_image text COLLATE pg_catalog."default",
          label character varying(255) COLLATE pg_catalog."default",
          active_attachment integer NOT NULL DEFAULT 0,
          deleted integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_49b0da9551096c6fd9fd69ace5f" PRIMARY KEY (id)
      )

    Table: product_price_chart
      CREATE TABLE IF NOT EXISTS public.product_price_chart
      (
          id integer NOT NULL DEFAULT nextval('product_price_chart_id_seq'::regclass),
          product_id integer NOT NULL,
          size_id integer NOT NULL,
          attachment_style_id integer NOT NULL,
          price_chart jsonb NOT NULL,
          deleted integer NOT NULL DEFAULT 0,
          created_at timestamp without time zone NOT NULL DEFAULT now(),
          updated_at timestamp without time zone NOT NULL DEFAULT now(),
          CONSTRAINT "PK_3b306976fff3e58acf6dc2cd161" PRIMARY KEY (id),
          CONSTRAINT "FK_8769953d1868308af72e3b19994" FOREIGN KEY (attachment_style_id)
              REFERENCES public.attachment_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_99ae9d2a58851d6e5a82471f298" FOREIGN KEY (size_id)
              REFERENCES public.size (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT,
          CONSTRAINT "FK_c8a360a6bd9c45149d0c1297cee" FOREIGN KEY (product_id)
              REFERENCES public.product (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )

    Table: attachment_styles
      CREATE TABLE IF NOT EXISTS public.attachment_styles
      (
          id integer NOT NULL DEFAULT nextval('attachment_styles_id_seq'::regclass),
          name character varying(255) COLLATE pg_catalog."default" NOT NULL,
          colors character varying(255) COLLATE pg_catalog."default",
          product_image text COLLATE pg_catalog."default",
          category_id integer,
          selected_attachment integer,
          deleted integer NOT NULL DEFAULT 0,
          is_premium boolean,
          extra_charge numeric(10,2) DEFAULT 0,
          premium_clip integer NOT NULL DEFAULT 0,
          CONSTRAINT "PK_ec11d3083091459a072972a5ebc" PRIMARY KEY (id),
          CONSTRAINT fk_category FOREIGN KEY (category_id)
              REFERENCES public.attachment_categories (id) MATCH SIMPLE
              ON UPDATE NO ACTION
              ON DELETE RESTRICT
      )


    INSTRUCTIONS:
    - Generate SQL queries based on user queries regarding product pricing information, size, and attachment styles.
    - The query should retrieve relevant product details, size, and attachment style from the corresponding tables, with the following mappings:
    
      - p.title AS product_name: Retrieves the product title from the product table, labeled as product_name.
      - ppc.product_id AS product_id: Retrieves the product ID from the product_price_chart table, labeled as product_id.
      - ppc.size_id AS size_id: Retrieves the size ID from the product_price_chart table, labeled as size_id.
      - s.name AS lanyardWidth: Retrieves the name of the size from the size table, labeled as lanyardWidth.
      - ac.label AS attachment_style: Retrieves the label for the attachment style from the attachment_categories table, labeled as attachment_style.
      - ppc.attachment_style_id AS attachment_style_id: Retrieves the attachment style ID from the product_price_chart table, labeled as attachment_style_id.
      - ac.active_attachment AS attachment_type: Retrieves whether the attachment is active from the attachment_categories table, labeled as attachment_type.
      - ppc.price_chart: Retrieves the price chart from the product_price_chart table.
      
    - Ensure to filter out deleted records by checking that `ppc.deleted = 0`.
    - Include a count of total matching records for pagination purposes using COUNT() OVER().

    EXAMPLES:
    1. User Query: "Get the price details for the blue lanyard in size M."
       Generated SQL:
       SELECT 
           ppc.id AS id,
           p.title AS product_name,
           ppc.product_id AS product_id,
           ppc.size_id AS size_id,
           s.name AS lanyardWidth,
           ac.label AS attachment_style,
           ppc.attachment_style_id AS attachment_style_id,
           ac.active_attachment AS attachment_type,
           ppc.price_chart,
           COUNT(*) OVER() AS total_count
       FROM 
           product_price_chart ppc
       JOIN 
           product p ON ppc.product_id = p.id
       JOIN 
           size s ON ppc.size_id = s.id
       JOIN 
           attachment_categories ac ON ppc.attachment_style_id = ac.id
       WHERE 
           ppc.deleted = 0 AND 
           s.name ILIKE '%M%' AND 
           ac.label ILIKE '%blue%'
       ORDER BY 
           ppc.id;

    2. User Query: "Show me the price for the red lanyard."
       Generated SQL:
       SELECT 
           ppc.id AS id,
           p.title AS product_name,
           ppc.product_id AS product_id,
           ppc.size_id AS size_id,
           s.name AS lanyardWidth,
           ac.label AS attachment_style,
           ppc.attachment_style_id AS attachment_style_id,
           ac.active_attachment AS attachment_type,
           ppc.price_chart,
           COUNT(*) OVER() AS total_count
       FROM 
           product_price_chart ppc
       JOIN 
           product p ON ppc.product_id = p.id
       JOIN 
           size s ON ppc.size_id = s.id
       JOIN 
           attachment_categories ac ON ppc.attachment_style_id = ac.id
       WHERE 
           ppc.deleted = 0 AND 
           ac.label ILIKE '%red%' AND 
           p.title ILIKE '%lanyard%'
       ORDER BY 
           ppc.id;
    """
    return system_instructions



PRICE_CALCULATION_PATTERNS = [
    "calculate price for",
    "what is the price for",
    "what is the price of pone with attachment",
    "price of lanyard",
    "what is the price of nylon lanyard",
    "what's the price of nylon lanyard",
    "show me price for nylon lanyard",
    "show me price of nylon lanyard",
    "get me price for nylon lanyard",
    "get me price of nylon lanyard",
    "find price of nylon lanyard",
    "find price for nylon lanyard",

]
QUANTITY_SYNONYMS = [r'quantity', r'count', r'number', r'amount', r'total']
SIZE_SYNONYMS = [r'width', r'height', r'size', r'dimension', r'volume']
ATTACHMENT_SYNONYMS = [r'attachment style', r'style', r'attachment']
MEASUREMENT_SYNONYMS = [r'measurement', r'size of', r'dimension of']

# Combine synonyms into regex patterns
def create_synonym_pattern(synonyms):
    return r'(' + '|'.join(synonyms) + r')\s*'

def check_user_query_details(user_query: str) -> bool:
    # Normalize the query to lower case
    normalized_query = user_query.lower()

    # Keywords to look for
    keywords = {
        "product_name": r"\b(?:product|item|pone)\b",  # Including 'pone' directly
        "width": r"\b(?:width)\b",                     # Match 'width'
        "attachment_style": r"\b(?:attachment|style|clip)\b",  # Match variations of 'attachment style'
        "quantity": r"\b(?:quantity|amount|number|of\s+\d+)\b" # Match 'quantity' and numbers
    }

    # Check for each keyword in the normalized query
    for key, pattern in keywords.items():
        if not re.search(pattern, normalized_query):
            return False  # Return false if any keyword is missing

    # Check specifically for a numeric quantity presence
    quantity_matches = re.search(r'\b\d+\b', normalized_query)
    if not quantity_matches:
        return False  # Return false if no numeric quantity found

    return True

# Create a ChatPromptTemplate with the dynamic user input
def create_dynamic_sql_prompt(user_query: str, customer_id: str) -> ChatPromptTemplate:
    
    is_recent_order_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in RECEIVED_ORDER_PATTERNS)
    is_price_calculation_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in PRICE_CALCULATION_PATTERNS)

    
REQUIRED_PATTERNS = {
    'attachment_style': ['attachment style', 'clip', 'style'],
    'width': ['width', 'size'],
    'quantity': ['quantity', 'amount'],
    'measurement': ['measurement', 'size']
}

  
def contains_all_required_info(user_query: str) -> bool:
    return (any(fuzz.ratio(user_query, pattern) > 80 for pattern in REQUIRED_PATTERNS['attachment_style']) and
            any(fuzz.ratio(user_query, pattern) > 80 for pattern in REQUIRED_PATTERNS['width']) and
            any(fuzz.ratio(user_query, pattern) > 80 for pattern in REQUIRED_PATTERNS['quantity']) and  
            any(fuzz.ratio(user_query, pattern) > 80 for pattern in REQUIRED_PATTERNS['measurement']))


def create_dynamic_user_response(user_query: str, title: str, order_id: str, total_price: str, status: str, product_id: str) -> ChatPromptTemplate:
    dynamic_prompt = get_dynamic_user_order_response()
    return ChatPromptTemplate.from_messages([
        ("system", dynamic_prompt),
        ("human", f"{user_query} | {title} | {order_id} | {total_price} | {product_id} | {status}")
    ])

def create_dynamic_user_product_response(user_query: str, title: str, product_id: str) -> ChatPromptTemplate:
    dynamic_prompt = get_dynamic_user_product_response()
    return ChatPromptTemplate.from_messages([
        ("system", dynamic_prompt),
        ("human", f"{user_query} | {title} | {product_id}")
    ])

def create_dynamic_user_price_response(user_query: str, title: str, price_chart: str, quantity: str, product_id: str) -> ChatPromptTemplate:
    dynamic_prompt = get_dynamic_user_price_response()
    return ChatPromptTemplate.from_messages([
        ("system", dynamic_prompt),
        ("human", f"{user_query} | {title} | {price_chart} | {quantity} | {product_id}")
    ])

def create_dynamic_sql_prompt(user_query: str, customer_id: str) -> ChatPromptTemplate:
    is_recent_order_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in RECEIVED_ORDER_PATTERNS)
    is_price_calculation_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in PRICE_CALCULATION_PATTERNS)
    is_price_and_quantity_query = check_user_query_details(user_query)

    print(f"{is_price_calculation_query}check condition",is_price_and_quantity_query, is_recent_order_query)
    if is_price_calculation_query:
       dynamic_prompt = get_dynamic_sql_prompt_price()
       return ChatPromptTemplate.from_messages([
            ("system", dynamic_prompt),
            ("human", f"{user_query}")
        ])
    elif is_price_and_quantity_query:
        dynamic_prompt = get_dynamic_sql_prompt_for_price_with_nearest_quantity_altered()
        return ChatPromptTemplate.from_messages([
            ("system", dynamic_prompt),
            ("human", f"{user_query}")
        ])
    elif is_recent_order_query:
        dynamic_prompt = get_dynamic_sql_prompt_order()
        return ChatPromptTemplate.from_messages([
            ("system", dynamic_prompt),
            ("human", f"{user_query} | {customer_id}")
        ])
    else:
        dynamic_prompt = get_dynamic_sql_prompt_product()
        return ChatPromptTemplate.from_messages([
            ("system", dynamic_prompt),
            ("human", f"{user_query}")
        ])


    # dynamic_prompt = get_dynamic_sql_prompt()
    # return ChatPromptTemplate.from_messages([
    #     ("system", dynamic_prompt),
    #     ("human", f"{user_query} | customer_id={customer_id}")
    # ])

# Patterns to identify order-related queries
RECEIVED_ORDER_PATTERNS = [
    "show me my recent order",
    "show me order",
    "show me the last order",
    "show me the first order",
    "show me the recent order",
    "show me my first order",
    "show my recent orders",
    "give me my latest order",
    "display my last order",
    "tell me about my last order",
    "show me recent orders",
    "show my orders",
    "what is my last order",
    "what i ordered last", "order price for", "price of the last order", "Show me the details of my order with number",
    "Show me the details of my order with id",
    "show me the order details of",
    "price of my last order", "what is the price of the last order",
    "price of my first order", "what is the price of the first order",
    "show me orders from last week.", "show me orders from this week.",
    "show me order status", "what is my order status", "what is the status of my last order", "what is the status of my order",
    "show the status of my order", "show the status of last order", "what's status of order"
]

# Define the chain that processes the input, generates the query, and returns results
@chain
def product_chain(x):
    user_query = x.get("message", "").strip().lower()
    customer_id = x.get("customer_id", "")

    greetings = ["hi", "hello", "hey", "greetings", "what's up", "howdy"]
    if any(greet in user_query for greet in greetings):
        # return "Hello! How can I assist you today?"
        return {
                          "message": f"Hello! How can I assist you today?",
                          "link": None,
                          "image": None,
                          "type":"TEXT"
                            }

    is_recent_order_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in RECEIVED_ORDER_PATTERNS)
    # Create the dynamic SQL prompt template based on the user query
    sql_prompt_template = create_dynamic_sql_prompt(user_query, customer_id)
    
    # Combine the dynamic prompt with the structured model for SQL generation
    sql_chain = sql_prompt_template | gemini_generative_model
    
    try:
        # Generate the SQL query with user_query
        result = sql_chain.invoke(input={"text": user_query, "user_query": user_query, "customer_id": customer_id})
        print(f"Chain Result: {result}")

        # Convert the result into JSON and extract the SQL query
        # query = json.loads(result.json())
        # print(f"Generated SQL Query: {query.get('query')}")
        is_price_calculation_query = any(fuzz.ratio(user_query, pattern) > 80 for pattern in PRICE_CALCULATION_PATTERNS)
        is_price_and_quantity_query = check_user_query_details(user_query)

        # Ensure the query is not None or empty
        # sql_query = query.get("query")
        sql_query = result.replace("```sql", "").replace("```", "").strip() # Clean the query by removing backticks
        if sql_query:
            # Execute the generated SQL query and return the result
            query_result = execute_query(sql_query)
            print(f"Query Result: {query_result}and{is_price_calculation_query}")
            
            # Analyze user query to determine the context of the response
            if query_result :
                if is_recent_order_query:
                    # Prepare the response format for recent orders
                    if query_result:
                        recent_order = query_result[0]
                        title = recent_order['title'].replace(" ","")
                        order_id = recent_order['id']
                        product_id = recent_order["product_id"]
                        status = recent_order["status"]
                        material = recent_order['material']
                        color = recent_order['color_name']
                        total_price = recent_order['total_price']
                        product_image_url = recent_order['product_image_url']
                        order_link = f"{os.getenv('DOMAIN_FE')}/pages/product-view?orderId={order_id}"
                        link = f"{os.getenv('DOMAIN_FE')}/product-details/{product_id}-{title}"
                        response_prompt_template = create_dynamic_user_response(user_query, title, order_id, total_price, status, product_id)
                        response_chain = response_prompt_template | gemini_generative_model
                        user_result = response_chain.invoke(input={"text": user_query, "title": title, "order_id": order_id, "total_price": total_price, "status": status, "product_id": product_id})
                        print(f"recent_order response: {recent_order} ")
                        # response_message = f"Hey, your recent order is {title}, with material: {material}, color: {color}, image: {product_image_url}. Here is where you can see more: {link}"
                        response_message = {
                          # "message": f"Hey, your recent order is {title}, of id: #{order_id}, total price: {total_price}",
                          "message": f"{user_result}",
                          "link": order_link,
                          "image": product_image_url,
                          "type":"ORDER"
                            }
                    else:
                        response_message = {
                           "message": "Sorry, no recent orders found.",
                           "link": None,
                           "image": None,
                           "type":"TEXT"
                          }
                elif is_price_calculation_query:
                    # Price calculation handling code
                    if query_result:
                        product_info = query_result[0]
                        price_chart = product_info['price_chart'][0]
                        title = product_info['title']
                        product_id = product_info['id']
                        product_image=product_info['url']
                        response_prompt_template = create_dynamic_user_price_response(user_query, title, price_chart['price'], price_chart['quantity'], product_id)
                        response_chain = response_prompt_template | gemini_generative_model
                        user_result = response_chain.invoke(input={"text": user_query, "title": title, "price_chart": price_chart['price'], "quantity":  price_chart['quantity'], "product_id": product_id})
                        print(f"user response: {user_result} ")
                        response_message = {
                            "message": f"{user_result}",
                            "link": None,
                            "image": product_image,
                            "type": "PRICE"
                        }
                elif is_price_and_quantity_query:
                     print(f"inside resp gen")
                     response = query_result[0]
                     price = response['price']
                     response_message = {
                          "message": f"The price for the product Matching your criteria is {price}",
                          "link": None,
                          "image": None,
                          "type":"PRODUCT"
                            }
                else:
                    if query_result:
                        base_url = os.getenv("BASE_URL")
                        recent_order = query_result[0]
                        title = recent_order['title'].replace(" ","")
                        product_id = recent_order["id"]
                        # material = recent_order['material']
                        # color = recent_order['color_name']
                        product_image_url = recent_order['url']
                        link = f"{os.getenv('DOMAIN_FE')}/product-details/{product_id}-{title}"
                        response_prompt_template = create_dynamic_user_product_response(user_query, title, product_id)
                        response_chain = response_prompt_template | gemini_generative_model
                        user_result = response_chain.invoke(input={"text": user_query, "title": title, "product_id": product_id})
                        print(f"user response: {user_result} ")
                        # response_message = f"Hey, your recent order is {title}, with material: {material}, color: {color}, image: {product_image_url}. Here is where you can see more: {link}"
                        response_message = {
                          "message": f"{user_result}",
                          "link": link,
                          "image": product_image_url,
                          "type":"PRODUCT"
                            }
                    # product_links = list({
                    #     f"http://ec2-44-202-158-140.compute-1.amazonaws.com:3000/product-details/{product['id']}"
                    #     for product in query_result if 'id' in product
                    # })
                    # response_message = f"Here are the products matching your criteria: {', '.join(product_links)}"
                    else:
                        response_message = {
                           "message": "Sorry, no recent orders found.",
                           "link": None,
                           "image": None,
                           "type":"TEXT"
                          }
            else:
                response_message = "Sorry, no results found based on your query."
        else:
            response_message = "Generated query was empty or invalid."
    
    except Exception as e:
        print(f"Error executing query: {e}")
        response_message = "Sorry, there was an error processing your query."
    
    # Create the final response structure
    return response_message

# Example Input for product query
input_data_product = {
    "message": "show me product with width more than 10"
}

# Example Input for order query
input_data_order = {
    "message": "what is my last order",
    "customer_id": "12345"  # Example customer_id
}

# Run the chain with the input and get the result for products
result_product = product_chain.invoke(input_data_product)
print(f"Product Query Result: {result_product}")

# Run the chain with the input and get the result for orders
result_order = product_chain.invoke(input_data_order)
print(f"Order Query Result: {result_order}")
