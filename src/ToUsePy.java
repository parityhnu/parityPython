import java.io.*;

public class ToUsePy {
    public static void main(String args[]){
        try {
            File directory = new File("");//设定为当前文件夹
            String dirPath = directory.getAbsolutePath();//获取绝对路径
            String pyPath = "\\src\\requestRedis";
            String exe = "python";
            String command = dirPath + pyPath;
            System.out.println(command);
            String index = "0";
            String good = "欧舒丹";
            String[] cmdArr = new String[] {exe, command, index, good};
            Process process = Runtime.getRuntime().exec(cmdArr);
            BufferedReader in = new BufferedReader(new InputStreamReader(
                    process.getInputStream()));
            String line;
            while ((line = in.readLine()) != null) {
                System.out.println(line);
            }
            in.close();
            process.waitFor();
            System.out.println("end");
        }catch (IOException e){
            System.out.println(e);
        }catch (InterruptedException e2){
            System.out.println(e2);
        }

    }
}
