resource "aws_glue_catalog_database" "yt" {
  name = "yt_pipeline"
}

resource "aws_glue_catalog_table" "curated" {
  name          = "yt_curated"
  database_name = aws_glue_catalog_database.yt.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification              = "parquet"
    "projection.enabled"        = "true"
    "projection.region.type"    = "enum"
    "projection.region.values"  = "IN,US,GB"
    "projection.dt.type"        = "date"
    "projection.dt.format"      = "yyyy-MM-dd"
    "projection.dt.range"       = "2026-10-01,NOW"
    "projection.hour.type"      = "integer"
    "projection.hour.range"     = "0,23"
    "projection.hour.digits"    = "2"
    "storage.location.template" = "s3://${var.bucket_name}/curated/region=$${region}/dt=$${dt}/hour=$${hour}/"
  }

  partition_keys {
    name = "region"
    type = "string"
  }

  partition_keys {
    name = "dt"
    type = "string"
  }

  partition_keys {
    name = "hour"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${var.bucket_name}/curated/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "video_id"
      type = "string"
    }

    columns {
      name = "title"
      type = "string"
    }

    columns {
      name = "channel_id"
      type = "string"
    }

    columns {
      name = "channel_title"
      type = "string"
    }

    columns {
      name = "category_id"
      type = "string"
    }

    columns {
      name = "published_at"
      type = "timestamp"
    }

    columns {
      name = "views"
      type = "bigint"
    }

    columns {
      name = "likes"
      type = "bigint"
    }

    columns {
      name = "comments"
      type = "bigint"
    }

    columns {
      name = "rank"
      type = "int"
    }

    columns {
      name = "ingested_at"
      type = "timestamp"
    }
  }
}

resource "aws_athena_workgroup" "yt" {
  name          = "yt-wg"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration = true
    bytes_scanned_cutoff_per_query  = 104857600

    result_configuration {
      output_location = "s3://${var.bucket_name}/athena-results/"
    }
  }
}
