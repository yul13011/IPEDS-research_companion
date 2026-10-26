import com.healthmarketscience.jackcess.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class InspectRelease {
  static void cell(Writer w,Object v)throws Exception {if(v==null)return;w.write('"');w.write(v.toString().replace("\"","\"\""));w.write('"');}
  static void row(Writer w,Object... vs)throws Exception{boolean first=true;for(Object v:vs){if(!first)w.write(',');first=false;cell(w,v);}w.write('\n');}
  public static void main(String[] args)throws Exception{
    File root=new File(args[0]),out=new File(args[1]);out.mkdirs();
    try(Writer schema=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(out,"database_schema.csv")),StandardCharsets.UTF_8));
        Writer samples=new BufferedWriter(new OutputStreamWriter(new FileOutputStream(new File(out,"database_samples.csv")),StandardCharsets.UTF_8))){
      row(schema,"release","table","source_rows","column","type","length","autonumber");
      row(samples,"release","table","sample_number","column","value");
      File[] folders=root.listFiles();java.util.Arrays.sort(folders);
      for(File folder:folders){if(!folder.isDirectory())continue;
        File[] files=folder.listFiles((d,n)->n.toLowerCase().endsWith(".accdb"));if(files.length!=1)throw new IOException("Expected one database "+folder);
        try(Database db=new DatabaseBuilder(files[0]).setReadOnly(true).open()){
          int nt=0;
          for(String name:db.getTableNames()){
            Table t=db.getTable(name);nt++;
            for(Column col:t.getColumns())row(schema,folder.getName(),name,t.getRowCount(),col.getName(),col.getType(),col.getLength(),col.isAutoNumber());
            int n=0;for(Row r:t){n++;for(Column col:t.getColumns())row(samples,folder.getName(),name,n,col.getName(),r.get(col.getName()));if(n==3)break;}
          }
          schema.flush();samples.flush();System.out.println(folder.getName()+": "+nt+" tables inspected");
        }
      }
    }
  }
}
