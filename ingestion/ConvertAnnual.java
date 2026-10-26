import com.healthmarketscience.jackcess.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.sql.Types;
import java.util.*;

/** Faithful read-only Access extraction; exact decimal fields remain TEXT. */
public class ConvertAnnual {
  static String q(String s){return "\""+s.replace("\"","\"\"")+"\"";}
  static String affinity(DataType t){
    switch(t){case BYTE:case INT:case LONG:case BIG_INT:case BOOLEAN:return "INTEGER";
      case FLOAT:case DOUBLE:return "REAL";
      case TEXT:case MEMO:case NUMERIC:case MONEY:case GUID:return "TEXT";
      default:throw new IllegalArgumentException("Unsupported source type: "+t);}
  }
  static Object canonical(Object v,String type){
    if(v==null)return null;
    if(type.equals("INTEGER"))return v instanceof Boolean?((Boolean)v?1L:0L):((Number)v).longValue();
    if(type.equals("REAL")){double d=((Number)v).doubleValue();if(!Double.isFinite(d))throw new IllegalArgumentException("Nonfinite source number");return d==0?0.0:d;}
    return v.toString();
  }
  static void digest(MessageDigest md,Object value){
    if(value==null){md.update((byte)0);return;}
    md.update((byte)1);byte[] b=value.toString().getBytes(StandardCharsets.UTF_8);
    int n=b.length;md.update((byte)(n>>>24));md.update((byte)(n>>>16));md.update((byte)(n>>>8));md.update((byte)n);md.update(b);
  }
  static String hex(byte[] a){StringBuilder b=new StringBuilder();for(byte x:a)b.append(String.format("%02x",x&255));return b.toString();}
  static void cell(Writer w,Object v)throws Exception{if(v==null)return;w.write('"');w.write(v.toString().replace("\"","\"\""));w.write('"');}
  static void row(Writer w,Object... values)throws Exception{boolean f=true;for(Object v:values){if(!f)w.write(',');f=false;cell(w,v);}w.write('\n');}
  public static void main(String[] args)throws Exception{
    File source=new File(args[0]),target=new File(args[1]),report=new File(args[2]);
    if(target.exists())throw new IOException("Refusing to overwrite "+target);
    target.getParentFile().mkdirs();report.mkdirs();Class.forName("org.sqlite.JDBC");
    try(Database access=new DatabaseBuilder(source).setReadOnly(true).open();
        Connection db=DriverManager.getConnection("jdbc:sqlite:"+target.getAbsolutePath());
        Writer cols=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(report,"columns.csv")),StandardCharsets.UTF_8));
        Writer checks=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(report,"table_checks.csv")),StandardCharsets.UTF_8))){
      row(cols,"table","column","ordinal","access_type","access_width","sqlite_type","null_count");
      row(checks,"table","source_rows","sqlite_rows","columns","source_values_sha256","sqlite_values_sha256","verified");
      try(Statement st=db.createStatement()){st.execute("PRAGMA journal_mode=DELETE");st.execute("PRAGMA synchronous=NORMAL");}
      db.setAutoCommit(false);long total=0;int tables=0;
      for(String name:access.getTableNames()){
        Table table=access.getTable(name);List<? extends Column> cs=table.getColumns();
        String[] affinities=new String[cs.size()];StringBuilder ddl=new StringBuilder("CREATE TABLE "+q(name)+" (");
        StringBuilder insert=new StringBuilder("INSERT INTO "+q(name)+" VALUES (");
        for(int i=0;i<cs.size();i++){
          affinities[i]=affinity(cs.get(i).getType());if(i>0){ddl.append(',');insert.append(',');}
          ddl.append(q(cs.get(i).getName())).append(' ').append(affinities[i]);insert.append('?');
        }
        ddl.append(')');insert.append(')');try(Statement st=db.createStatement()){st.execute(ddl.toString());}
        long count=0;long[] nulls=new long[cs.size()];MessageDigest src=MessageDigest.getInstance("SHA-256");
        try(PreparedStatement st=db.prepareStatement(insert.toString())){
          for(Row r:table){
            src.update((byte)2);
            for(int i=0;i<cs.size();i++){
              Object v=canonical(r.get(cs.get(i).getName()),affinities[i]);digest(src,v);
              if(v==null){nulls[i]++;st.setNull(i+1,Types.NULL);}
              else if(v instanceof Long)st.setLong(i+1,(Long)v);
              else if(v instanceof Double)st.setDouble(i+1,(Double)v);
              else st.setString(i+1,(String)v);
            }
            st.addBatch();count++;if(count%5000==0)st.executeBatch();
          }
          st.executeBatch();
        }
        if(count!=table.getRowCount())throw new IOException("Source row count mismatch: "+name);
        db.commit();MessageDigest dst=MessageDigest.getInstance("SHA-256");long verified=0;long[] checkNulls=new long[cs.size()];
        try(Statement st=db.createStatement();ResultSet rs=st.executeQuery("SELECT * FROM "+q(name)+" ORDER BY rowid")){
          while(rs.next()){
            dst.update((byte)2);verified++;
            for(int i=0;i<cs.size();i++){
              Object v=canonical(rs.getObject(i+1),affinities[i]);digest(dst,v);if(v==null)checkNulls[i]++;
            }
          }
        }
        String a=hex(src.digest()),b=hex(dst.digest());
        if(count!=verified||!Arrays.equals(nulls,checkNulls)||!a.equals(b))throw new IOException("Verification failed: "+name);
        for(int i=0;i<cs.size();i++){
          Column col=cs.get(i);row(cols,name,col.getName(),i,col.getType(),col.getLength(),affinities[i],nulls[i]);
          if(col.getName().equalsIgnoreCase("UNITID"))try(Statement st=db.createStatement()){st.execute("CREATE INDEX "+q("idx_"+name+"_UNITID")+" ON "+q(name)+" ("+q(col.getName())+")");}
        }
        db.commit();row(checks,name,count,verified,cs.size(),a,b,true);checks.flush();cols.flush();total+=count;tables++;
        System.out.println(name+": "+count+" rows; all values and nulls verified");
      }
      try(Statement st=db.createStatement();ResultSet rs=st.executeQuery("PRAGMA integrity_check")){
        if(!rs.next()||!"ok".equals(rs.getString(1)))throw new IOException("SQLite integrity check failed");
      }
      db.commit();System.out.println("COMPLETE "+tables+" tables "+total+" rows; integrity_check=ok");
    }
  }
}
